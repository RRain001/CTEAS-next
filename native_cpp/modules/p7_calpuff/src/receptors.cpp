#include "cteas/puff/receptors.hpp"

#include <algorithm>
#include <charconv>
#include <cmath>
#include <cstddef>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace cteas::puff {
namespace {

using R = float;   // the vendor PFSAMP/ERFDIF state is REAL*4

constexpr double kTwoPi = 6.2831853;
constexpr double kSquareRootTwo = 1.4142136;    // RT2 in PFSAMP
constexpr double kSqrtPiByTwo = 1.2533141;      // RTPIBY2 in PFSAMP
constexpr double kLowWindThreshold = 1.0e-4;    // A < 1.e-4 shortcut

void require_true(bool condition, const std::string& message) {
    if (!condition) throw std::invalid_argument("P7E receptors: " + message);
}

void require_finite(double value, const std::string& what) {
    require_true(std::isfinite(value), what + " must be finite");
}

double required_option_double(const ControlFile& control, const char* key) {
    const auto found = control.values(key);
    require_true(found.size() == 1U, std::string("expected exactly one active control: ") + key);
    std::string raw = found.front();
    for (char& c : raw) {
        if (c == 'D' || c == 'd') c = 'E';
    }
    std::size_t consumed = 0;
    double value = 0.0;
    try {
        value = std::stod(raw, &consumed);
    } catch (const std::exception&) {
        throw std::invalid_argument(std::string("P7E receptors: invalid float option ") + key + "=" +
                                    found.front());
    }
    require_true(consumed == raw.size() && std::isfinite(value),
                 std::string("invalid or non-finite float option ") + key + "=" + found.front());
    return value;
}

int required_option_int(const ControlFile& control, const char* key) {
    const auto found = control.values(key);
    require_true(found.size() == 1U, std::string("expected exactly one active control: ") + key);
    int value = 0;
    const std::string& raw = found.front();
    const auto [end, error] = std::from_chars(raw.data(), raw.data() + raw.size(), value);
    require_true(end == raw.data() + raw.size() && error == std::errc{},
                 std::string("P7E receptors: invalid integer option ") + key + "=" + raw);
    return value;
}

std::string trim(const std::string& value) {
    const auto first = value.find_first_not_of(" \t\r\n");
    if (first == std::string::npos) return {};
    const auto last = value.find_last_not_of(" \t\r\n");
    return value.substr(first, last - first + 1);
}

std::vector<std::string> lines_of(const std::string& text) {
    std::vector<std::string> lines;
    std::istringstream stream(text);
    std::string line;
    while (std::getline(stream, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        lines.push_back(line);
    }
    return lines;
}

std::vector<std::string> section_lines(const std::vector<std::string>& lines, const std::string& marker) {
    std::vector<std::string> section;
    bool inside = false;
    for (const auto& line : lines) {
        if (!inside) {
            if (line.find(marker) != std::string::npos) inside = true;
            continue;
        }
        if (trim(line).rfind("!END!", 0) == 0U) break;
        section.push_back(line);
    }
    return section;
}

double parse_number(const std::string& raw, const std::string& what) {
    std::string text = trim(raw);
    for (char& c : text) {
        if (c == 'D' || c == 'd') c = 'E';
    }
    std::size_t consumed = 0;
    double value = 0.0;
    try {
        value = std::stod(text, &consumed);
    } catch (const std::exception&) {
        throw std::invalid_argument("P7E receptors: invalid value for " + what + ": " + raw);
    }
    require_true(consumed == text.size() && std::isfinite(value),
                 "invalid or non-finite value for " + what + ": " + raw);
    return value;
}

bool parse_logical(const ControlFile& control, const char* key) {
    const auto found = control.values(key);
    require_true(found.size() == 1U, std::string("expected exactly one active control: ") + key);
    std::string value = found.front();
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) {
        return static_cast<char>(std::toupper(c));
    });
    if (value == "T" || value == "TRUE" || value == ".TRUE." || value == "YES" || value == "1") {
        return true;
    }
    if (value == "F" || value == "FALSE" || value == ".FALSE." || value == "NO" || value == "0") {
        return false;
    }
    throw std::invalid_argument("P7E receptors: invalid logical option " + std::string(key) + "=" +
                                found.front());
}

// Discrete receptor subgroup 17b: `! N = X, Y, ZELEV, ZRCT !` with the columns
// documented in the control file (X/Y in km, elevation and height in m).
std::vector<Receptor> parse_discrete_receptors(const std::vector<std::string>& lines) {
    static const std::regex row(R"(^\s*!\s*(\d+)\s*=\s*([^!]*)!\s*$)");
    std::vector<Receptor> receptors;
    for (const auto& line : lines) {
        std::smatch match;
        if (!std::regex_match(line, match, row)) continue;
        std::vector<double> values;
        std::string list = match[2].str();
        std::size_t start = 0;
        while (true) {
            const auto comma = list.find(',', start);
            const std::string piece =
                list.substr(start, comma == std::string::npos ? std::string::npos : comma - start);
            if (!trim(piece).empty() || comma != std::string::npos) {
                values.push_back(parse_number(piece, "discrete receptor " + match[1].str()));
            }
            if (comma == std::string::npos) break;
            start = comma + 1;
        }
        require_true(values.size() == 3U || values.size() == 4U,
                     "discrete receptor " + match[1].str() + " must give X, Y, ZELEV [, ZRCT]");
        Receptor receptor;
        receptor.x_km = values[0];
        receptor.y_km = values[1];
        receptor.ground_elevation_m = values[2];
        receptor.height_m = values.size() == 4U ? values[3] : 0.0;
        receptors.push_back(receptor);
    }
    return receptors;
}

} // namespace

double erf_difference(double x1, double x2) {
    // ERFDIF (calpuff.for L54910-54965), REAL*4 arithmetic.
    const R a = static_cast<R>(x1);
    const R b = static_cast<R>(x2);
    if (a == b) return 0.0;
    if (static_cast<double>(a) * static_cast<double>(b) <= 0.0) {
        return static_cast<double>(std::erf(a) - std::erf(b));
    }
    const R test = std::min(std::abs(a), std::abs(b));
    if (test >= 9.15F) return 0.0;
    if (test < 0.47F) return static_cast<double>(std::erf(a) - std::erf(b));
    const R sign = a > 0.0F ? 1.0F : -1.0F;
    const R first = std::abs(a);
    const R second = std::abs(b);
    const R erfc_first = first < 9.15F ? std::erfc(first) : 0.0F;
    const R erfc_second = second < 9.15F ? std::erfc(second) : 0.0F;
    R difference = sign * (erfc_second - erfc_first);
    if (erfc_second == erfc_first) difference = 0.0F;
    return static_cast<double>(difference);
}

PuffScreeningResult original_puff_screen(
    double x_old,double y_old,double x_new,double y_new,
    double x_receptor,double y_receptor,double puff_radius_squared) {
    for(double v:{x_old,y_old,x_new,y_new,x_receptor,y_receptor,puff_radius_squared})
        require_finite(v,"PFSCRN input");
    require_true(puff_radius_squared>0.0,"PFSCRN radius squared must be positive");
    // Vendor calpuff.for L4649-4678. Preserve REAL*4 and MIN/MAX order.
    const R dx=static_cast<R>(x_new)-static_cast<R>(x_old);
    const R dy=static_cast<R>(y_new)-static_cast<R>(y_old);
    const R dx1=static_cast<R>(x_old)-static_cast<R>(x_receptor);
    const R dy1=static_cast<R>(y_old)-static_cast<R>(y_receptor);
    const R c1=dx*dx+dy*dy;
    const R radius2=static_cast<R>(puff_radius_squared);
    require_true(std::isfinite(radius2)&&radius2>0.0F,
                 "PFSCRN radius squared underflows/overflows REAL4");
    const R a=c1/radius2;
    R dist2=0.0F;
    const bool calm=a<1.0e-4F;
    if(calm){
        const R rx=static_cast<R>(x_receptor) -
                   (static_cast<R>(x_old)+0.5F*dx);
        const R ry=static_cast<R>(y_receptor) -
                   (static_cast<R>(y_old)+0.5F*dy);
        dist2=rx*rx+ry*ry;
    }else{
        const R c2=dx*dx1+dy*dy1;
        R fraction=-c2/c1;
        fraction=std::max(fraction,0.0F);
        fraction=std::min(fraction,1.0F);
        const R nearest_x=static_cast<R>(x_old)+dx*fraction;
        const R nearest_y=static_cast<R>(y_old)+dy*fraction;
        const R rx=static_cast<R>(x_receptor)-nearest_x;
        const R ry=static_cast<R>(y_receptor)-nearest_y;
        dist2=rx*rx+ry*ry;
    }
    require_true(std::isfinite(dist2),"PFSCRN nearest-distance overflow");
    return {static_cast<double>(dist2),dist2<=radius2,calm};
}

SamplingIntegrals puff_sampling_integrals(double x_old_km, double y_old_km, double x_new_km,
                                          double y_new_km, double x_receptor_km,
                                          double y_receptor_km, double sigma_y_at_receptor_m,
                                          double closest_approach_squared_km2) {
    for (const auto& [value, name] :
         {std::pair<double, const char*>{x_old_km, "x_old"}, {y_old_km, "y_old"},
          {x_new_km, "x_new"}, {y_new_km, "y_new"}, {x_receptor_km, "x_receptor"},
          {y_receptor_km, "y_receptor"}, {sigma_y_at_receptor_m, "sigma_y at receptor"},
          {closest_approach_squared_km2, "closest-approach distance squared"}}) {
        require_finite(value, name);
    }
    require_true(sigma_y_at_receptor_m > 0.0, "sigma_y at receptor must be positive");
    require_true(closest_approach_squared_km2 >= 0.0,
                 "closest-approach distance squared must not be negative");

    // PFSAMP (calpuff.for L4683-4751): REAL*4 throughout.
    const R xold = static_cast<R>(x_old_km);
    const R yold = static_cast<R>(y_old_km);
    const R xnew = static_cast<R>(x_new_km);
    const R ynew = static_cast<R>(y_new_km);
    const R xrec = static_cast<R>(x_receptor_km);
    const R yrec = static_cast<R>(y_receptor_km);
    const R sygu = static_cast<R>(sigma_y_at_receptor_m);
    const R dist2 = static_cast<R>(closest_approach_squared_km2);

    SamplingIntegrals integrals;
    const R dx = xnew - xold;
    const R dy = ynew - yold;
    const R dx1 = xold - xrec;
    const R dy1 = yold - yrec;
    const R c1 = dx * dx + dy * dy;
    const R tsy = sygu * sygu;
    const R a = c1 / tsy;
    if (a < static_cast<R>(kLowWindThreshold)) {
        // Original PFSAMP L4732-4733 uses REAL4 XI2 and then REAL4 XI1.
        // Do not re-import the widened public double member to form XI1.
        const R xi2 = 0.5F * std::exp(-dist2 / (2.0F * tsy));
        const R xi1 = 2.0F * xi2;
        integrals.i2 = static_cast<double>(xi2);
        integrals.i1 = static_cast<double>(xi1);
        integrals.low_wind_branch = true;
        return integrals;
    }
    const R sqrta = std::sqrt(a);
    const R sqrt2a = static_cast<R>(kSquareRootTwo) * sqrta;
    const R c2 = dx * dx1 + dy * dy1;
    const R b = c2 / tsy;
    const R c = (dx1 * dx1 + dy1 * dy1) / tsy;
    const R xxexp = std::exp(0.5F * (b * b / a - c));
    integrals.i1 = static_cast<R>(kSqrtPiByTwo) / sqrta * xxexp *
                   static_cast<R>(erf_difference(static_cast<double>((a + b) / sqrt2a),
                                                 static_cast<double>(b / sqrt2a)));
    const R b2da = b * b / a;
    // Vendor PFSAMP L4746-4748: XI1 and XI2 are distinct default REAL*4
    // variables. SamplingIntegrals exposes double storage at the public
    // C++ boundary, so using integrals.i1 here promotes -B*XI1/A to REAL*8
    // and loses the intermediate REAL*4 rounding performed by Fortran.
    // Keep XI1 and the entire XI2 expression in float before widening only
    // the finished result to the interface type.
    const R xi1 = static_cast<R>(integrals.i1);
    const R xi2 = (-b * xi1 / a) +
                  (xxexp / a) * (std::exp(-0.5F * b2da) -
                                std::exp(-0.5F * (a + 2.0F * b + b2da)));
    integrals.i2 = static_cast<double>(xi2);
    return integrals;
}

double receptor_concentration_increment(const SamplingIntegrals& integrals,
                                        const ReceptorAccumulationInputs& inputs) {
    require_finite(integrals.i1, "sampling integral I1");
    require_finite(integrals.i2, "sampling integral I2");
    require_finite(inputs.mass_old, "start-of-step mass");
    require_finite(inputs.mass_new, "end-of-step mass");
    require_finite(inputs.sigma_y_at_receptor_m, "sigma_y at receptor");
    require_true(inputs.sigma_y_at_receptor_m > 0.0, "sigma_y at receptor must be positive");
    require_finite(inputs.vertical_factor, "vertical coupling factor");
    require_true(inputs.vertical_factor >= 0.0, "vertical coupling factor must not be negative");
    require_finite(inputs.time_fraction, "time fraction");
    require_true(inputs.time_fraction > 0.0 && inputs.time_fraction <= 1.0,
                 "time fraction must be in (0,1]");
    require_finite(inputs.deposition_ratio, "deposition ratio");
    require_true(inputs.deposition_ratio >= 0.0, "deposition ratio must not be negative");
    require_finite(inputs.area_source_factor, "area source distribution factor");
    require_true(inputs.area_source_factor >= 0.0,
                 "area source distribution factor must not be negative");

    // CALCPF gridded-receptor branch: normalize by 1/(2*pi*sigma_y**2) and
    // weight the start/end masses by the two sampling integrals.
    const R sigma = static_cast<R>(inputs.sigma_y_at_receptor_m);
    // Vendor CALCPF L4293: ASDF/(6.2831853*SYREC**2).
    // The exponent evaluates SYREC*SYREC in REAL*4 *before* multiplying
    // by 6.2831853. Left-associated (2*pi*sigma)*sigma instead rounds
    // a different intermediate and can perturb T1/T2 and concentration.
    const R sigma_squared = sigma * sigma;
    const R denominator = static_cast<R>(kTwoPi) * sigma_squared;
    const R inverse = static_cast<R>(inputs.area_source_factor) /
                      denominator;
    const R t2 = static_cast<R>(integrals.i2) * inverse;
    const R t1 = static_cast<R>(integrals.i1) * inverse - t2;
    // Original CALCPF L4304: CONC = VDPVD(IPOL)*XTEMP*
    // (QOLD(IPOL)*T1+QNEW(IPOL)*T2), with XTEMP=F1*TFRACT
    // formed as one REAL4 intermediate. Keeping this grouping is
    // essential now that the uniform-puff DRY VDPVD is non-unity.
    const R xtemp=static_cast<R>(inputs.vertical_factor) *
                  static_cast<R>(inputs.time_fraction);
    const R concentration =
        static_cast<R>(inputs.deposition_ratio) * xtemp *
        (static_cast<R>(inputs.mass_old) * t1 +
         static_cast<R>(inputs.mass_new) * t2);
    require_true(std::isfinite(concentration), "accumulated concentration must be finite");
    return static_cast<double>(concentration);
}

double receptor_concentration_increment_with_coupling(const SamplingIntegrals& integrals,
                                                     const ReceptorAccumulationInputs& inputs,
                                                     const VcbarInputs& coupling) {
    auto coupled = inputs;
    coupled.vertical_factor = vertical_coupling_bar(coupling);
    return receptor_concentration_increment(integrals, coupled);
}

ReceptorSet receptors_from_control(const std::string& control_text) {
    const auto control = ControlFile::parse(control_text);
    const auto lines = lines_of(control_text);

    ReceptorSet receptors;
    const int met_nx = required_option_int(control, "NX");
    const int met_ny = required_option_int(control, "NY");
    const double dgrid_km = required_option_double(control, "DGRIDKM");
    const double x_origin_km = required_option_double(control, "XORIGKM");
    const double y_origin_km = required_option_double(control, "YORIGKM");
    const int ibcomp = required_option_int(control, "IBCOMP");
    const int jbcomp = required_option_int(control, "JBCOMP");
    const int iecomp = required_option_int(control, "IECOMP");
    const int jecomp = required_option_int(control, "JECOMP");
    require_true(met_nx > 0 && met_ny > 0, "met grid dimensions must be positive");
    require_true(dgrid_km > 0.0, "DGRIDKM must be positive");
    require_true(ibcomp >= 1 && jbcomp >= 1 && iecomp <= met_nx && jecomp <= met_ny &&
                     ibcomp <= iecomp && jbcomp <= jecomp,
                 "computational grid indices must lie inside the met grid");

    receptors.gridded = parse_logical(control, "LSAMP");
    receptors.mesh_down = required_option_int(control, "MESHDN");
    require_true(receptors.mesh_down >= 1, "MESHDN must be at least 1");
    receptors.ibsamp = required_option_int(control, "IBSAMP");
    receptors.jbsamp = required_option_int(control, "JBSAMP");
    receptors.iesamp = required_option_int(control, "IESAMP");
    receptors.jesamp = required_option_int(control, "JESAMP");
    require_true(receptors.ibsamp >= 1 && receptors.jbsamp >= 1 &&
                     receptors.iesamp <= met_nx && receptors.jesamp <= met_ny &&
                     receptors.ibsamp <= receptors.iesamp &&
                     receptors.jbsamp <= receptors.jesamp,
                 "sampling grid indices must lie inside the met grid");
    require_true(receptors.ibsamp >= ibcomp && receptors.jbsamp >= jbcomp &&
                     receptors.iesamp <= iecomp && receptors.jesamp <= jecomp,
                 "sampling grid must be a subset of the computational grid");
    receptors.spacing_km = dgrid_km / static_cast<double>(receptors.mesh_down);
    receptors.sampling_nx = receptors.mesh_down * (receptors.iesamp - receptors.ibsamp) + 1;
    receptors.sampling_ny = receptors.mesh_down * (receptors.jesamp - receptors.jbsamp) + 1;

    receptors.discrete = parse_discrete_receptors(
        section_lines(lines, "NON-GRIDDED (DISCRETE) RECEPTOR DATA"));
    require_true(receptors.gridded || !receptors.discrete.empty(),
                 "deck enables neither gridded nor discrete receptors");
    for (const auto& receptor : receptors.discrete) {
        require_finite(receptor.x_km, "discrete receptor X");
        require_finite(receptor.y_km, "discrete receptor Y");
        require_finite(receptor.ground_elevation_m, "discrete receptor elevation");
        require_finite(receptor.height_m, "discrete receptor height");
        require_true(receptor.height_m >= 0.0, "discrete receptor height must not be negative");
        const double local_x = receptor.x_km - x_origin_km;
        const double local_y = receptor.y_km - y_origin_km;
        require_true(local_x >= -1.0e-6 && local_y >= -1.0e-6 &&
                         local_x <= dgrid_km * met_nx + 1.0e-6 &&
                         local_y <= dgrid_km * met_ny + 1.0e-6,
                     "discrete receptor lies outside the met grid");
    }

    if (receptors.gridded) {
        // Vendor convention (calpuff.for L5640): the first receptor sits at
        // (IBSAMP-0.5)*DGRID and each further receptor adds DELSAM = DGRID/MESHDN.
        receptors.grid.reserve(static_cast<std::size_t>(receptors.sampling_nx) *
                               static_cast<std::size_t>(receptors.sampling_ny));
        for (int j = 0; j < receptors.sampling_ny; ++j) {
            for (int i = 0; i < receptors.sampling_nx; ++i) {
                Receptor receptor;
                receptor.x_km = x_origin_km +
                                (static_cast<double>(receptors.ibsamp) - 0.5) * dgrid_km +
                                static_cast<double>(i) * receptors.spacing_km;
                receptor.y_km = y_origin_km +
                                (static_cast<double>(receptors.jbsamp) - 0.5) * dgrid_km +
                                static_cast<double>(j) * receptors.spacing_km;
                receptors.grid.push_back(receptor);
            }
        }
    }
    return receptors;
}

ReceptorSet receptors_from_original_met_grid(
    const std::string& control_text, const OriginalMetGridFrame& met) {
    validate_original_met_frame(met);
    auto receptors = receptors_from_control(control_text);
    if (!receptors.gridded || receptors.mesh_down != 1) {
        throw std::invalid_argument(
            "P7 original QA grid mapping currently supports gridded MESHDN=1");
    }
    // The selected P7 2022 original deck has DGRIDKM=0.1 matching the
    // original CALMET.DAT 100 m horizontal spacing. Do not silently map a
    // different control geometry onto that meteorological frame.
    const float control_spacing_km = static_cast<float>(receptors.spacing_km);
    const float met_spacing_km = met.spacing_m * 0.001f;
    if (!std::isfinite(control_spacing_km) ||
        std::abs(control_spacing_km - met_spacing_km) > 1.0e-6f) {
        throw std::invalid_argument("P7 CALPUFF control/CALMET grid spacing mismatch");
    }
    for (int j = 0; j < receptors.sampling_ny; ++j) {
        for (int i = 0; i < receptors.sampling_nx; ++i) {
            const auto qa = original_gridded_receptor_qa_xy(
                met, receptors.ibsamp - 1 + i, receptors.jbsamp - 1 + j);
            auto& receptor = receptors.grid[static_cast<std::size_t>(j) *
                                                  static_cast<std::size_t>(receptors.sampling_nx) +
                                              static_cast<std::size_t>(i)];
            receptor.x_km = static_cast<double>(qa.x_km);
            receptor.y_km = static_cast<double>(qa.y_km);
        }
    }
    return receptors;
}

} // namespace cteas::puff
