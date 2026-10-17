#pragma once

#include <cstdint>

namespace cteas::puff {

// Proleptic Gregorian calendar helpers shared by the original CALMET.DAT
// reader and the P7 case ledger. Valid for the selected 1900-2100 original
// date range; callers validate the year before using the result.

// Days since 1970-01-01, leap-century correct (Howard Hinnant's civil algorithm).
[[nodiscard]] std::int64_t days_from_civil(int year, unsigned month, unsigned day);

// Absolute UTC instant of an explicit Gregorian date/time in seconds.
[[nodiscard]] std::int64_t gregorian_unix_seconds(int year, int month, int day,
                                                  int hour, int seconds);

} // namespace cteas::puff
