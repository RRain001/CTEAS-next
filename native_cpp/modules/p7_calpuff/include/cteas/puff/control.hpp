#pragma once

#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

namespace cteas::puff {

struct ControlEntry {
    std::string key;
    std::string value;
    std::size_t line = 0;
};

class ControlFile {
public:
    static ControlFile parse(std::string_view text);
    static ControlFile read_file(const std::string& path);

    [[nodiscard]] std::vector<std::string> values(std::string_view key) const;
    [[nodiscard]] std::string required_one(std::string_view key) const;
    [[nodiscard]] int required_int(std::string_view key) const;
    [[nodiscard]] std::vector<double> required_float_list(std::string_view key) const;
    [[nodiscard]] const std::vector<ControlEntry>& entries() const noexcept { return entries_; }
private:
    std::vector<ControlEntry> entries_;
};

// Only a selected *input* contract. Physics/transport, MET.DAT binary decoding,
// species chemistry, deposition and reference-output parity are not yet implemented.
struct SelectedDryInputs {
    std::string met_file;
    int nx = 0;
    int ny = 0;
    int nz = 0;
    int time_step_s = 0;
    int species_count = 0;
    int emitted_species_count = 0;
    int output_units = 0;
    std::vector<double> zface_m;
};

[[nodiscard]] SelectedDryInputs validate_selected_dry_inputs(const ControlFile& control);

} // namespace cteas::puff
