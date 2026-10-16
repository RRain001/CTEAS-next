// P7I CTSG support blocks (QATR integrator, TFAC terrain factors) tests.
// Hand-derived closed forms plus fail-closed behaviour; original-routine parity
// is checked by tests/p7i_parity_tests.py against the compiled vendor units.
#include "cteas/puff/ctsg.hpp"

#include <cmath>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("P7I TEST FAILURE: " + message);
}

void require_close(double observed, double expected, double tolerance, const std::string& what) {
    require(std::abs(observed - expected) <= tolerance,
            what + ": observed " + std::to_string(observed) + " expected " +
                std::to_string(expected) + " tolerance " + std::to_string(tolerance));
}

template <typename Callable>
void require_throw(Callable&& callable, const std::string& what) {
    bool threw = false;
    try {
        callable();
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    require(threw, what + " must fail closed");
}

void test_qatr() {
    const auto sine = cteas::puff::integrate_romberg(0.0, 3.14159265358979, 1.0e-6, 30,
                                                     [](double x) { return std::sin(x); });
    require(sine.status == cteas::puff::QuadratureStatus::converged, "sine converges");
    require_close(sine.value, 2.0, 1.0e-4, "integral of sin over [0,pi]");

    const auto square = cteas::puff::integrate_romberg(0.0, 1.0, 1.0e-6, 30,
                                                       [](double x) { return x * x; });
    require(square.status == cteas::puff::QuadratureStatus::converged, "x^2 converges");
    require_close(square.value, 1.0 / 3.0, 1.0e-6, "integral of x^2 over [0,1]");

    const auto exponential = cteas::puff::integrate_romberg(
        0.0, 5.0, 1.0e-6, 30, [](double x) { return std::exp(-x); });
    require_close(exponential.value, 1.0 - std::exp(-5.0), 1.0e-5, "integral of exp(-x)");

    // A function that is identically zero takes the vendor's zero-over-interval path.
    const auto zero = cteas::puff::integrate_romberg(0.0, 1.0, 1.0e-6, 30, [](double) { return 0.0; });
    require(zero.status == cteas::puff::QuadratureStatus::converged && zero.value == 0.0,
            "zero integrand converges to zero");

    // A constant function is integrated exactly by the first trapezoid step.
    const auto constant = cteas::puff::integrate_romberg(1.0, 3.0, 1.0e-6, 30,
                                                         [](double) { return 1.0; });
    require_close(constant.value, 2.0, 1.0e-6, "integral of a constant");

    // Zero-width interval and the single-level request follow the vendor flags.
    const auto degenerate = cteas::puff::integrate_romberg(2.0, 2.0, 1.0e-6, 30,
                                                           [](double x) { return x; });
    require(degenerate.status == cteas::puff::QuadratureStatus::converged &&
                degenerate.value == 0.0,
            "zero-width interval");
    const auto single = cteas::puff::integrate_romberg(0.0, 1.0, 1.0e-6, 1, [](double) { return 1.0; });
    require(single.status == cteas::puff::QuadratureStatus::no_convergence,
            "single-level request reports no convergence");

    // A function that diverges on refinement reports the diverging flag.
    int calls = 0;
    const auto diverging = cteas::puff::integrate_romberg(0.0, 1.0, 1.0e-9, 20,
                                                          [&calls](double) { return ++calls; });
    require(diverging.status != cteas::puff::QuadratureStatus::converged,
            "non-convergent integrand must not report convergence");

    require_throw([] { (void)cteas::puff::integrate_romberg(0.0, 1.0, 0.0, 10, [](double) { return 1.0; }); },
                  "zero tolerance");
    require_throw([] { (void)cteas::puff::integrate_romberg(0.0, 1.0, 1.0e-6, 0, [](double) { return 1.0; }); },
                  "dimension below one");
    require_throw([] {
        (void)cteas::puff::integrate_romberg(0.0, 1.0, 1.0e-6, 10,
                                             std::function<double(double)>());
    }, "missing integrand");
    std::cout << "P7I_QATR_CONTRACT=PASS SIN=" << sine.value << " X2=" << square.value << "\n";
}

void test_tfac() {
    const std::vector<double> top{1.0, 1.5, 2.0, 2.5};
    const std::vector<double> lateral{1.0, 0.5, 0.25, 0.125};
    // Outside [begin, end] the factors are unity.
    const auto outside_low = cteas::puff::terrain_factors(0.5, 1.0, 4.0, 1.0, top, lateral);
    require(outside_low.top == 1.0 && outside_low.lateral == 1.0 && outside_low.total == 1.0,
            "outside the terrain window");
    const auto outside_high = cteas::puff::terrain_factors(4.5, 1.0, 4.0, 1.0, top, lateral);
    require(outside_high.total == 1.0, "above the terrain window");
    // Interpolation between the first two nodes: at x=1.5 the fraction is 0.5.
    const auto middle = cteas::puff::terrain_factors(1.5, 1.0, 4.0, 1.0, top, lateral);
    require_close(middle.top, 1.25, 1.0e-6, "interpolated TH");
    require_close(middle.lateral, 0.75, 1.0e-6, "interpolated TL");
    require_close(middle.total, 1.0 / (1.25 * 0.75), 1.0e-6, "TU = 1/(TH*TL)");
    // Exactly on the first node.
    const auto node = cteas::puff::terrain_factors(1.25, 1.0, 4.0, 1.0, top, lateral);
    require_close(node.top, 1.125, 1.0e-6, "TH at a quarter node");

    require_throw([&] {
        (void)cteas::puff::terrain_factors(2.0, 1.0, 4.0, 0.0, top, lateral);
    }, "zero spacing");
    require_throw([&] {
        (void)cteas::puff::terrain_factors(2.0, 4.0, 1.0, 1.0, top, lateral);
    }, "inverted window");
    require_throw([&] {
        (void)cteas::puff::terrain_factors(2.0, 1.0, 4.0, 1.0, top, {});
    }, "mismatched factor arrays");
    require_throw([&] {
        (void)cteas::puff::terrain_factors(3.9, 1.0, 4.0, 1.0, {1.0, 1.0}, {1.0, 1.0});
    }, "arrays too short for the position");
    std::cout << "P7I_TFAC_CONTRACT=PASS\n";
}

int matrix_mode(const std::string& which) {
    std::cout.setf(std::ios::scientific, std::ios::floatfield);
    std::cout.precision(12);
    if (which == "--qatr-matrix") {
        std::size_t cases = 0;
        while (true) {
            int icase = 0, code = 0, dimension = 0;
            double lower = 0.0, upper = 0.0, eps = 0.0;
            if (!(std::cin >> icase >> code >> lower >> upper >> eps >> dimension)) {
                if (std::cin.eof()) break;
                throw std::invalid_argument("malformed QATR case line");
            }
            const auto integrand = [code](double x) {
                if (code == 1) return std::sin(x);
                if (code == 2) return x * x;
                if (code == 3) return std::exp(-x);
                if (code == 4) return 0.0;
                return 1.0;
            };
            const auto result =
                cteas::puff::integrate_romberg(lower, upper, eps, dimension, integrand);
            std::cout << icase << ' ' << result.value << ' '
                      << static_cast<int>(result.status) << '\n';
            ++cases;
        }
        std::cerr << "P7I_QATR_MATRIX=PASS CASES=" << cases << "\n";
        return 0;
    }
    if (which == "--rotate-matrix") {
        std::size_t cases = 0;
        while (true) {
            int icase = 0;
            double x = 0.0, y = 0.0, angle = 0.0;
            if (!(std::cin >> icase >> x >> y >> angle)) {
                if (std::cin.eof()) break;
                throw std::invalid_argument("malformed ROTATE case line");
            }
            const auto result = cteas::puff::rotate_xy(x, y, angle);
            std::cout << icase << ' ' << result.x << ' ' << result.y << '\n';
            ++cases;
        }
        std::cerr << "P7I_ROTATE_MATRIX=PASS CASES=" << cases << "\n";
        return 0;
    }
    if (which == "--tfac-matrix") {
        std::size_t cases = 0;
        while (true) {
            int icase = 0, points = 0;
            double x = 0.0, begin = 0.0, end = 0.0, spacing = 0.0;
            if (!(std::cin >> icase >> x >> begin >> end >> spacing >> points) || points <= 0) {
                if (std::cin.eof()) break;
                throw std::invalid_argument("malformed TFAC case line");
            }
            std::vector<double> top(static_cast<std::size_t>(points));
            std::vector<double> lateral(static_cast<std::size_t>(points));
            for (int i = 0; i < points; ++i) {
                if (!(std::cin >> top[static_cast<std::size_t>(i)] >>
                      lateral[static_cast<std::size_t>(i)])) {
                    throw std::invalid_argument("malformed TFAC factor row");
                }
            }
            const auto result = cteas::puff::terrain_factors(x, begin, end, spacing, top, lateral);
            std::cout << icase << ' ' << result.top << ' ' << result.lateral << ' ' << result.total
                      << '\n';
            ++cases;
        }
        std::cerr << "P7I_TFAC_MATRIX=PASS CASES=" << cases << "\n";
        return 0;
    }
    throw std::invalid_argument("unknown matrix mode " + which);
}

void test_rotate() {
    const auto quarter = cteas::puff::rotate_xy(1.0, 0.0, 3.14159265358979 / 2.0);
    require_close(quarter.x, 0.0, 1.0e-6, "rotated x at 90 degrees");
    require_close(quarter.y, -1.0, 1.0e-6, "rotated y at 90 degrees");
    const auto identity = cteas::puff::rotate_xy(2.0, -3.0, 0.0);
    require_close(identity.x, 2.0, 1.0e-9, "identity x");
    require_close(identity.y, -3.0, 1.0e-9, "identity y");
    // Rotation preserves the radius.
    const auto rotated = cteas::puff::rotate_xy(1.5, 2.5, 0.7);
    require_close(std::sqrt(rotated.x * rotated.x + rotated.y * rotated.y),
                  std::sqrt(1.5 * 1.5 + 2.5 * 2.5), 1.0e-6, "rotation preserves radius");
    require_throw([] { (void)cteas::puff::rotate_xy(1.0, 1.0, std::nan("")); }, "NaN angle");
    std::cout << "P7I_ROTATE_CONTRACT=PASS\n";
}

} // namespace

int main(int argc, char** argv) {
    try {
        if (argc == 2 && (std::string(argv[1]) == "--qatr-matrix" ||
                          std::string(argv[1]) == "--tfac-matrix" ||
                          std::string(argv[1]) == "--rotate-matrix")) {
            return matrix_mode(argv[1]);
        }
        test_qatr();
        test_tfac();
        test_rotate();
        std::cout << "P7I_CTSG_SUPPORT_CONTRACT=PASS\n"
                     "P7I_IS_NOT_A_CONCENTRATION_PARITY_TEST=true\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\n";
        return 1;
    }
}
