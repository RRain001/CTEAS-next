#pragma once
// Exact-source, selected-Hefei-2022 P6-to-P7 input integrity admission.
// This checks byte binding; self-attested producer identity is NOT a
// cryptographic signature. A trusted runner must control source and evidence.
#include <string>

namespace cteas::puff {
void verify_native_p6_admission(const std::string& evidence_file,
                                const std::string& p6_manifest,
                                const std::string& p6_driver,
                                const std::string& met_file,
                                const std::string& source_sha,
                                int requested_hours);
}
