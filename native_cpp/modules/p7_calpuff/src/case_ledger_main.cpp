#include "cteas/puff/case_ledger.hpp"

#include <exception>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>

namespace {
constexpr const char* kUsage =
    "Usage: cteas_p7_2022_case_ledger --met MET.DAT --control CALPUFF.INP\n"
    "       [--concentration PATH] [--listing PATH] [--report PATH]\n"
    "       [--expect-met-sha256 HEX] [--expect-control-sha256 HEX]\n"
    "Exit codes: 0 accepted canonical 2022 case, 3 blocked missing inputs,\n"
    "            4 rejected not a canonical 2022 case, 2 usage, 1 internal error.\n";
} // namespace

int main(int argc, char** argv) {
    cteas::puff::CaseLedgerRequest request;
    std::string report_path;
    try {
        for (int index = 1; index < argc; ++index) {
            const std::string option = argv[index];
            if (option == "--help" || option == "-h") {
                std::cout << kUsage;
                return 0;
            }
            const auto value = [&index, argc, argv, &option]() {
                if (index + 1 >= argc) throw std::invalid_argument("P7 missing value for " + option);
                return std::string(argv[++index]);
            };
            if (option == "--met") request.met_path = value();
            else if (option == "--control") request.control_path = value();
            else if (option == "--concentration") request.concentration_path = value();
            else if (option == "--listing") request.listing_path = value();
            else if (option == "--report") report_path = value();
            else if (option == "--expect-met-sha256") request.expected_met_sha256 = value();
            else if (option == "--expect-control-sha256") request.expected_control_sha256 = value();
            else throw std::invalid_argument("P7 unknown option: " + option);
        }
        if (request.met_path.empty() || request.control_path.empty()) {
            throw std::invalid_argument("P7 --met and --control are both required");
        }
    } catch (const std::exception& error) {
        std::cerr << "P7 CASE LEDGER USAGE ERROR: " << error.what() << "\n" << kUsage;
        return 2;
    }

    try {
        const auto result = cteas::puff::evaluate_hefei_2022_case(request);
        const auto document = cteas::puff::case_ledger_json(result);
        std::cout << document;
        if (!report_path.empty()) {
            std::ofstream out(report_path);
            if (!out) throw std::runtime_error("P7 cannot write ledger report: " + report_path);
            out << document;
            out.close();
            if (!out) throw std::runtime_error("P7 ledger report write failed: " + report_path);
        }
        std::cerr << "P7_2022_EXECUTION_LEDGER_STATUS=" << result.status
                  << " CANONICAL_2022=" << (result.canonical_2022 ? "true" : "false")
                  << " CHECKS=" << result.checks.size()
                  << " NOT_A_PHYSICS_PARITY_TEST=true\n";
        return result.exit_code;
    } catch (const std::exception& error) {
        std::cerr << "P7 CASE LEDGER INTERNAL ERROR: " << error.what() << "\n";
        return 1;
    }
}
