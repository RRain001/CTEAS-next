// P6F evidence helper: apply fixed, documented perturbations to the *values* of
// a legal CALMET.DAT 2.1 file and write the result with the P6F writer.
//
// It exists so the reader-exercising evidence of this module can show that the
// unmodified original CALPUFF reads changed-but-legal numbers rather than only a
// byte-identical file. It never changes the record structure, the field masks,
// the units, the time labels or the controls, and it never touches a value that
// already carries the XMISS sentinel:
//
//   --scale-wind F    multiply every U-LEV/V-LEV/WFACE value by F
//   --scale-zi F      multiply every ZI value by F
//   --shift-tempk K   add K to every TEMPK value
//
// The original is not modified and no physics is claimed: this is a test helper.
#include "cteas/p6f/calmet_dat21_writer.hpp"
#include "cteas/p6f/sha256.hpp"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using cteas::p6f::Calmet21Field;
using cteas::p6f::Calmet21File;

std::string trim(const std::string& text) {
    const auto first = text.find_first_not_of(' ');
    if(first == std::string::npos)return std::string();
    const auto last = text.find_last_not_of(' ');
    return text.substr(first, last - first + 1U);
}
std::string json_number(double value) {
    if(!std::isfinite(value))return "null";
    char buffer[64];
    std::snprintf(buffer, sizeof(buffer), "%.9g", value);
    return buffer;
}
std::string json_string(const std::string& text) { return "\"" + text + "\""; }

struct Touched {
    std::string name;
    std::string operation;
    std::size_t values = 0;
    double before = 0.0;
    double after = 0.0;
};

bool scale_field(Calmet21Field& field, const std::string& name, double factor,
                 double offset, const char* operation, Touched& touched) {
    if(field.integer)return false;
    const std::string label = trim(field.label);
    if(label.rfind(name, 0U) != 0U)return false;
    bool seen = false;
    for(float& value : field.real_values) {
        if(cteas::p6f::is_missing(value))continue;
        if(!seen) {
            touched.before = static_cast<double>(value);
            seen = true;
        }
        value = static_cast<float>(static_cast<double>(value) * factor + offset);
        touched.after = static_cast<double>(value);
        ++touched.values;
    }
    touched.name = name;
    touched.operation = operation;
    return true;
}

}  // namespace

int main(int argc, char** argv) {
    const std::vector<std::string> args(argv + 1, argv + argc);
    std::string input, output, report;
    double scale_wind = 1.25, scale_zi = 1.5, shift_tempk = 5.0;
    try {
        for(std::size_t at = 0; at < args.size(); ++at) {
            const std::string& flag = args[at];
            const auto value = [&args, &at, &flag]() {
                if(at + 1U >= args.size())
                    throw std::runtime_error(flag + " requires a value");
                return args[++at];
            };
            if(flag == "--in")input = value();
            else if(flag == "--out")output = value();
            else if(flag == "--report")report = value();
            else if(flag == "--scale-wind")
                scale_wind = std::atof(value().c_str());
            else if(flag == "--scale-zi")scale_zi = std::atof(value().c_str());
            else if(flag == "--shift-tempk")
                shift_tempk = std::atof(value().c_str());
            else throw std::runtime_error("unknown option " + flag);
        }
        if(input.empty() || output.empty())
            throw std::runtime_error("--in and --out are required");
        if(!(scale_wind > 0.0) || !(scale_zi > 0.0))
            throw std::runtime_error("wind and ZI factors must be positive");

        const Calmet21File original = cteas::p6f::read_calmet_dat21(input);
        Calmet21File changed = original;
        std::vector<Touched> touched;
        std::size_t scaled_winds = 0, scaled_zi = 0, shifted_temp = 0;
        for(Calmet21Field& field : changed.hourly) {
            const std::string label = trim(field.label);
            for(const char* name : {"U-LEV", "V-LEV", "WFACE"}) {
                if(label.rfind(name, 0U) != 0U)continue;
                Touched entry;
                if(scale_field(field, name, scale_wind, 0.0, "scale", entry)) {
                    touched.push_back(entry);
                    ++scaled_winds;
                }
            }
            if(label.rfind("ZI", 0U) == 0U) {
                Touched entry;
                if(scale_field(field, "ZI", scale_zi, 0.0, "scale", entry)) {
                    touched.push_back(entry);
                    ++scaled_zi;
                }
            }
            if(label.rfind("TEMPK", 0U) == 0U) {
                Touched entry;
                if(scale_field(field, "TEMPK", 1.0, shift_tempk, "shift",
                               entry)) {
                    touched.push_back(entry);
                    ++shifted_temp;
                }
            }
        }
        if(scaled_winds == 0U || scaled_zi == 0U || shifted_temp == 0U)
            throw std::runtime_error(
                "the input has no U/V/W, ZI or TEMPK field to perturb");

        const std::vector<std::uint8_t> bytes =
            cteas::p6f::serialize_calmet_dat21(changed);
        std::ofstream out(output, std::ios::binary | std::ios::trunc);
        if(!out)throw std::runtime_error("cannot create " + output);
        out.write(reinterpret_cast<const char*>(bytes.data()),
                  static_cast<std::streamsize>(bytes.size()));
        out.close();
        if(!out)throw std::runtime_error("short write to " + output);

        std::string text;
        text += "{\n  \"helper\": \"cteas_p6f_calmet_dat21_perturb\",\n";
        text += "  \"in\": " + json_string(input) + ",\n";
        text += "  \"in_sha256\": " +
                json_string(cteas::p6f::sha256_hex_file(input)) + ",\n";
        text += "  \"out\": " + json_string(output) + ",\n";
        text += "  \"out_sha256\": " +
                json_string(cteas::p6f::sha256_hex(bytes)) + ",\n";
        text += "  \"out_bytes\": " + std::to_string(bytes.size()) + ",\n";
        text += "  \"scale_wind\": " + json_number(scale_wind) + ",\n";
        text += "  \"scale_zi\": " + json_number(scale_zi) + ",\n";
        text += "  \"shift_tempk\": " + json_number(shift_tempk) + ",\n";
        text += "  \"structure_unchanged\": true,\n";
        text += "  \"sentinel_values_untouched\": true,\n";
        text += "  \"records_changed\": {\"wind\": " +
                std::to_string(scaled_winds) + ", \"zi\": " +
                std::to_string(scaled_zi) + ", \"tempk\": " +
                std::to_string(shifted_temp) + "},\n";
        text += "  \"first_change_per_field\": [\n";
        for(std::size_t k = 0; k < touched.size(); ++k) {
            const Touched& entry = touched[k];
            text += "    {\"field\": " + json_string(entry.name) +
                    ", \"operation\": " + json_string(entry.operation) +
                    ", \"values\": " + std::to_string(entry.values) +
                    ", \"before\": " + json_number(entry.before) +
                    ", \"after\": " + json_number(entry.after) + "}" +
                    (k + 1U == touched.size() ? "\n" : ",\n");
        }
        text += "  ],\n  \"status\": \"PASS_DOCUMENTED_PERTURBATION\"\n}\n";
        if(!report.empty()) {
            std::ofstream file(report, std::ios::binary | std::ios::trunc);
            if(!file)throw std::runtime_error("cannot create report " + report);
            file << text;
        }
        std::cout << "P6F_PERTURBED sha256="
                  << cteas::p6f::sha256_hex(bytes)
                  << " bytes=" << bytes.size() << " wind_records="
                  << scaled_winds << " zi_records=" << scaled_zi
                  << " tempk_records=" << shifted_temp << "\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr << "P6F_PERTURB_ERROR " << error.what() << "\n";
        return 1;
    }
}
