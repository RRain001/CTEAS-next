// P7W contract test: the ported RISEWIND against hand-computed vendor semantics,
// plus every fail-closed refusal.
#include "cteas/puff/rise_wind.hpp"

#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {

int failures = 0;
int checks = 0;

void check(bool condition, const std::string& what) {
    ++checks;
    if (!condition) {
        ++failures;
        std::cerr << "FAIL: " << what << '\n';
    }
}

void check_close(double got, double want, double tolerance, const std::string& what) {
    ++checks;
    if (!(std::abs(got - want) <= tolerance)) {
        ++failures;
        std::cerr << "FAIL: " << what << " got=" << got << " want=" << want << '\n';
    }
}

template <typename Callable>
void check_refuses(Callable&& callable, const std::string& what) {
    ++checks;
    try {
        callable();
        ++failures;
        std::cerr << "FAIL: " << what << " did not refuse\n";
    } catch (const std::invalid_argument&) {
        // expected
    }
}

} // namespace

int main() {
    using namespace cteas::puff;

    // A rise trajectory and an advective wind that make every RISEWIND branch
    // observable: the wind grows with height, so a wider rise layer gives a
    // different average.
    const auto rise = [](double x) { return 70.8 + 120.0 * (1.0 - std::exp(-x / 400.0)); };
    const auto wind = [](double zbot, double ztop) {
        AdvectiveWind result;
        result.u_ms = 0.1 * zbot + 0.2 * ztop - 0.5;
        result.v_ms = 0.3 * zbot - 0.1 * ztop + 1.0;
        return result;
    };
    const auto run = [&](double xbeg, double xfinal, double zfinal, double dzb, double dt,
                         double ufnl, double vfnl, int iterations) {
        RiseWindInputs inputs;
        inputs.puff = true;
        inputs.iterations = iterations;
        inputs.dz_m = dzb;
        inputs.start_distance_m = xbeg;
        inputs.final_distance_m = xfinal;
        inputs.final_height_m = zfinal;
        inputs.step_seconds = dt;
        inputs.u_final_ms = ufnl;
        inputs.v_final_ms = vfnl;
        inputs.wind_speed_ms = std::hypot(ufnl, vfnl);
        return transitional_rise_wind(inputs, rise, wind);
    };

    // Fully risen (XBEG >= XFINAL): the rise layer is fixed around ZFINAL, and the
    // blend uses FFINAL = 1 - XFINAL/XEND.
    {
        const double zfinal = 190.8;
        const double dzb = 10.0;
        const double xfinal = 1000.0;
        const double xbeg = 1200.0;
        const double ufnl = 1.0;
        const double vfnl = 2.0;
        const double dt = 60.0;
        // First pass: WS starts from the wind at the start-of-step layer.
        const double rbot0 = zfinal - dzb;
        const double rtop0 = zfinal + dzb;
        const auto start = wind(rbot0, rtop0);
        double ws = std::max(std::hypot(start.u_ms, start.v_ms), kRiseWindCalmSpeedMs);
        for (int pass = 0; pass < 2; ++pass) {
            const double xend = xbeg + ws * dt;
            const double rbot = std::max(zfinal - dzb, 0.0);
            const double rtop = zfinal + dzb;
            const auto average = wind(rbot, rtop);
            const double ffinal = 1.0 - xfinal / xend;
            const double uadv = (1.0 - ffinal) * average.u_ms + ffinal * ufnl;
            const double vadv = (1.0 - ffinal) * average.v_ms + ffinal * vfnl;
            ws = std::hypot(uadv, vadv);
            if (pass == 1) {
                const auto result = run(xbeg, xfinal, zfinal, dzb, dt, ufnl, vfnl, 2);
                check_close(result.u_ms, uadv, 1.0e-5, "risewind fully-risen u");
                check_close(result.v_ms, vadv, 1.0e-5, "risewind fully-risen v");
                check_close(result.wind_speed_ms, ws, 1.0e-5, "risewind fully-risen ws");
                check(result.passes == 2, "risewind ran NCOUNT passes");
            }
        }
    }

    // Still rising: the rise heights come from the trajectory at XBEG and XEND.
    {
        const double xbeg = 100.0;
        const double xfinal = 1500.0;
        const double zfinal = 190.8;
        const double dzb = 8.0;
        const double dt = 30.0;
        const auto result = run(xbeg, xfinal, zfinal, dzb, dt, 1.0, 1.0, 2);
        check(result.passes == 2, "risewind rising passes");
        // The vendor's arithmetic, recomputed here pass by pass.
        const double rbeg = rise(xbeg);
        const auto start_wind = wind(std::max(rbeg - dzb, 0.0), rbeg + dzb);
        double ws = std::max(std::hypot(start_wind.u_ms, start_wind.v_ms), kRiseWindCalmSpeedMs);
        double uadv = 1.0;
        double vadv = 1.0;
        for (int pass = 0; pass < 2; ++pass) {
            const double xend = xbeg + ws * dt;
            // The vendor takes the final-rise HEIGHT (not the trajectory) once the
            // step reaches the distance of final rise.
            const double rend = xend < xfinal ? rise(xend) : zfinal;
            const double rbot = std::max(std::min(rbeg, rend) - dzb, 0.0);
            const double rtop = std::max(rbeg, rend) + dzb;
            const auto average = wind(rbot, rtop);
            if (xend > xfinal) {
                const double ffinal = 1.0 - xfinal / xend;
                uadv = (1.0 - ffinal) * average.u_ms + ffinal * 1.0;
                vadv = (1.0 - ffinal) * average.v_ms + ffinal * 1.0;
            } else {
                uadv = average.u_ms;
                vadv = average.v_ms;
            }
            ws = std::hypot(uadv, vadv);
        }
        check_close(result.u_ms, uadv, 1.0e-5, "risewind rising u");
        check_close(result.v_ms, vadv, 1.0e-5, "risewind rising v");
    }

    // A single pass must equal the first iteration.
    {
        const auto one = run(100.0, 1500.0, 190.8, 8.0, 30.0, 1.0, 1.0, 1);
        check(one.passes == 1, "risewind honours NCOUNT=1");
    }

    // The falling branch (REND < RBEG) keeps RBOT at the lower of the two.
    {
        const auto falling_rise = [](double x) { return 200.0 - 0.05 * x; };
        RiseWindInputs inputs;
        inputs.iterations = 1;
        inputs.dz_m = 5.0;
        inputs.start_distance_m = 10.0;
        inputs.final_distance_m = 100000.0;
        inputs.final_height_m = 0.0;
        inputs.step_seconds = 600.0;
        inputs.u_final_ms = 1.0;
        inputs.v_final_ms = 1.0;
        inputs.wind_speed_ms = std::sqrt(2.0);
        const auto result = transitional_rise_wind(inputs, falling_rise, wind);
        const double rbeg = falling_rise(10.0);
        const auto start_wind = wind(std::max(rbeg - 5.0, 0.0), rbeg + 5.0);
        const double start_ws = std::hypot(start_wind.u_ms, start_wind.v_ms);
        const double rend = falling_rise(10.0 + start_ws * 600.0);
        check(rend < rbeg, "the falling fixture really falls");
        const double rbot = std::max(rend - 5.0, 0.0);
        const double rtop = rbeg + 5.0;
        const auto average = wind(rbot, rtop);
        check_close(result.u_ms, average.u_ms, 1.0e-5, "risewind falling u");
        check_close(result.v_ms, average.v_ms, 1.0e-5, "risewind falling v");
    }

    // The calm floor: a zero start wind still advances by ucalm*dt.
    {
        const auto zero_wind = [](double, double) {
            AdvectiveWind result;
            result.u_ms = 0.0;
            result.v_ms = 0.0;
            return result;
        };
        RiseWindInputs inputs;
        inputs.iterations = 1;
        inputs.dz_m = 5.0;
        inputs.start_distance_m = 0.0;
        inputs.final_distance_m = 1000.0;
        inputs.final_height_m = 100.0;
        inputs.step_seconds = 1000.0;
        inputs.u_final_ms = 0.0;
        inputs.v_final_ms = 0.0;
        inputs.wind_speed_ms = 0.0;
        const auto result = transitional_rise_wind(inputs, rise, zero_wind);
        check_close(result.wind_speed_ms, 0.0, 1.0e-9, "risewind calm ws");
    }

    // Fail-closed refusals.
    check_refuses([&] { run(0.0, 1000.0, 100.0, 5.0, 0.0, 1.0, 1.0, 2); },
                  "risewind refuses a non-positive step");
    check_refuses([&] { run(0.0, 1000.0, 100.0, 5.0, 60.0, 1.0, 1.0, 0); },
                  "risewind refuses NCOUNT=0");
    {
        RiseWindInputs inputs;
        inputs.iterations = 1;
        inputs.step_seconds = 60.0;
        inputs.start_distance_m = std::nan("");
        check_refuses([&] { (void)transitional_rise_wind(inputs, rise, wind); },
                      "risewind refuses a NaN start distance");
        check_refuses([&] { (void)transitional_rise_wind(inputs, {}, wind); },
                      "risewind refuses a missing rise lookup");
        check_refuses([&] { (void)transitional_rise_wind(inputs, rise, {}); },
                      "risewind refuses a missing wind lookup");
    }

    std::cout << "P7W_RISE_WIND_CONTRACT=" << (failures == 0 ? "PASS" : "FAIL")
              << " CHECKS=" << checks << " FAILURES=" << failures << '\n';
    return failures == 0 ? 0 : 1;
}
