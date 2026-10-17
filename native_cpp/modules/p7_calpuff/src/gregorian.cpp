#include "cteas/puff/gregorian.hpp"

namespace cteas::puff {

std::int64_t days_from_civil(int year, unsigned month, unsigned day) {
    year -= (month <= 2U) ? 1 : 0;
    const int era = (year >= 0 ? year : year - 399) / 400;
    const unsigned yoe = static_cast<unsigned>(year - era * 400);
    const unsigned month_shifted = month > 2U ? month - 3U : month + 9U;
    const unsigned doy = (153U * month_shifted + 2U) / 5U + day - 1U;
    const unsigned doe = yoe * 365U + yoe / 4U - yoe / 100U + doy;
    return static_cast<std::int64_t>(era) * 146097 + static_cast<int>(doe) - 719468;
}

std::int64_t gregorian_unix_seconds(int year, int month, int day, int hour, int seconds) {
    return days_from_civil(year, static_cast<unsigned>(month), static_cast<unsigned>(day)) * 86400 +
           static_cast<std::int64_t>(hour) * 3600 + seconds;
}

} // namespace cteas::puff
