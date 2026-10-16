#pragma once
// COORDLIB (GCTP 2.0.2) UTM inverse, ported verbatim from the CALMET 6.5.0
// vendor source so the P6E grid geometry matches the original bit-for-bit.
//
// Why this exists
//   The original CALMET converts each grid cell centre (km, REAL*4) to
//   N.lat/E.lon through `MICROI -> GLOBE1 -> GLOBE -> COORDS -> GTPZ0 ->
//   PJ01Z0 -> PJ09Z0` (calmet.for L9575-9603, coordlib.for).
//   `PJ09Z0` is the *TRANSVERSE MERCATOR* module; `GTPZ0` routes INSYS=1
//   (UTM) through `PJ01Z0`, which is a thin wrapper around `PJ09Z0`
//   (coordlib.for L5336-5364).  The MAP/COORDLIB naming is confusing: the
//   *polyconic* module is `PJ07Z0` (L5851) and is NOT used by UTM.  The
//   earlier E41 note in docs/reconstruction_cpp/P6E_PARALLEL_START_20261011.md
//   named `PJ07Z0`; the correct port target is `PJ09Z0` (this header).
//
// Ported routines (unmodified `coordlib.for`, sha256
// abe1d9a69ed7a4b8fa98bf1092cd668feef9f5612619ae3a8b565ec5b9be3c93):
//   * PJ09Z0  inverse transformation, IND=0 branch (L6107-6166)
//   * MLFNZ0  meridional-arc series (L3374-3385)
//   * ADJLZ0  longitude modulo 2*pi (L2658-2670)
//   * ASINZ0  guarded arcsine (L2686-2700)
//   * E0FNZ0..E3FNZ0  GCTP meridional-arc coefficients (L2733-2802)
//   * SPHDZ0  spheroid AXIS/BXIS tables (L7957-8086); spheroid 12 = WGS 84
//   * PJINIT UTM branch + label 900 initialisation (L3873-3894, L4443-4487)
//
// Initialisation for UTM zone N / WGS-84, exactly as COORDLIB does it:
//   A   = 6378137.0, B = 6356752.314245   (SPHDZ0 AXIS(13)/BXIS(13), ISPH=12)
//   ES  = 1 - (B/A)^2
//   E0..E3 from the ES polynomials
//   KS0 = 0.9996, X0 = 500000 m, Y0 = 0 m, LAT0 = 0, ML0 = 0
//   LON0 = PAKRZ0(1.0D6*(6*zone-183)) = (zone*6-183)*3600 * SECRAD
//   ESP = ES/(1-ES), IND = 0
// The inverse works on metres and returns RADIANS internally; the public
// helper applies COORDLIB's own conversion factor
// `FACTRS(5,1) = 0.5729577951308231D2` (degrees per radian), which is *not*
// 180/pi to the last bit - this matters for the REAL*4 rounding.
#include <cmath>
#include <stdexcept>
namespace cteas::p6e {
namespace coordlib_detail {
// --- ADJLZ0 (coordlib.for L2658-2670) -------------------------------------
inline constexpr double kPi=3.14159265358979323846;
inline double adjlz0(double lon) {
    while(std::fabs(lon)>kPi)lon=lon-std::copysign(2.0*kPi,lon);
    return lon;
}
// --- ASINZ0 (coordlib.for L2686-2700) -------------------------------------
inline double asinz0(double con) {
    if(std::fabs(con)>1.0)con=std::copysign(1.0,con);
    return std::asin(con);
}
// --- E0FNZ0..E3FNZ0 (coordlib.for L2733-2802) -----------------------------
inline double e0_fn(double es) {
    return 1.0-0.25*es*(1.0+es/16.0*(3.0+1.25*es));
}
inline double e1_fn(double es) {
    return 0.375*es*(1.0+0.25*es*(1.0+0.46875*es));
}
inline double e2_fn(double es) {
    return 0.05859375*es*es*(1.0+0.75*es);
}
inline double e3_fn(double es) {
    return es*es*es*(35.0/3072.0);
}
// --- MLFNZ0 (coordlib.for L3374-3385) -------------------------------------
inline double mlfnz0(double e0,double e1,double e2,double e3,double phi) {
    return e0*phi-e1*std::sin(2.0*phi)+e2*std::sin(4.0*phi)-e3*std::sin(6.0*phi);
}
// --- SPHDZ0 tables (coordlib.for L7999-8011), WGS-84 = spheroid 12 ---------
inline constexpr double kWgs84A=6378137.0;
inline constexpr double kWgs84B=6356752.314245;
// --- COORDLIB's own unit conversion FACTRS(5,1): radians -> degrees --------
inline constexpr double kGctpRadToDeg=0.5729577951308231e2;
// --- PAKRZ0/PAKSZ0 for a whole-degree packed angle (coordlib.for L3425-3480)
inline double pakrz0_degrees(double packed_degrees) {
    // PAKSZ0: split DDDMMMSSS.SS fields; here the UTM central-meridian
    // argument is always a whole degree count times 1.0D6.
    double ang=packed_degrees;
    const double factor=ang<0.0?-1.0:1.0;
    double sec=std::fabs(ang);
    int i=static_cast<int>(sec/1.0e6+1.0e-4);
    double deg=static_cast<double>(i);
    sec=sec-deg*1.0e6;
    i=static_cast<int>(sec/1.0e3+1.0e-4);
    double mins=static_cast<double>(i);
    sec=sec-mins*1.0e3;
    sec=factor*(deg*3600.0+mins*60.0+sec);
    return sec*0.4848136811095359e-5;
}
} // namespace coordlib_detail
// Reference-system parameters, the /PJ09/ common block after PJINIT.
struct UtmProjection {
    int zone=0;
    double A=0.0,LON0=0.0,X0=0.0,Y0=0.0;
    double ES=0.0,ESP=0.0,E0=0.0,E1=0.0,E2=0.0,E3=0.0;
    double KS0=0.0,LAT0=0.0,ML0=0.0;
    bool polar=false; // IND: 1 = spherical/polar branch, 0 = ellipsoidal
};
// PJINIT UTM branch + label 900 (coordlib.for L3873-3894, L4443-4487).
// `a`/`b` are the spheroid semi-axes (WGS-84 by default).
inline UtmProjection utm_north_projection(int zone,double a=coordlib_detail::kWgs84A,
                                          double b=coordlib_detail::kWgs84B) {
    if(zone<1||zone>60)throw std::invalid_argument("UTM zone outside 1..60");
    UtmProjection p;
    p.zone=zone;
    p.A=a;
    p.ES=1.0-(b/a)*(b/a);
    p.E0=coordlib_detail::e0_fn(p.ES);
    p.E1=coordlib_detail::e1_fn(p.ES);
    p.E2=coordlib_detail::e2_fn(p.ES);
    p.E3=coordlib_detail::e3_fn(p.ES);
    p.KS0=0.9996;
    p.LON0=coordlib_detail::pakrz0_degrees(1.0e6*(6.0*zone-183.0));
    p.X0=500000.0;
    p.Y0=0.0;
    p.LAT0=0.0;
    p.ML0=p.A*coordlib_detail::mlfnz0(p.E0,p.E1,p.E2,p.E3,p.LAT0);
    // SPHDZ0 eccentricity; COORDLIB's IND is set from E (not ES).
    const double e=std::sqrt(p.ES);
    p.polar=e<1.0e-5;
    p.ESP=p.polar?p.ES:p.ES/(1.0-p.ES);
    return p;
}
// PJ09Z0 inverse transformation (coordlib.for L6107-6166), IND=0 branch.
// Input: projected coordinates in METRES. Output: longitude and latitude in
// RADIANS, in that order (CRDIO(1),CRDIO(2)).
inline void pj09z0_inverse(const UtmProjection& p,double easting_m,double northing_m,
                           double& lon_rad,double& lat_rad) {
    using namespace coordlib_detail;
    const double X=easting_m-p.X0;
    const double Y=northing_m-p.Y0;
    if(p.polar) { // IND=1 spherical branch (not used for UTM N)
        const double F=std::exp(X/(p.A*p.KS0));
        const double G=0.5*(F-1.0/F);
        const double TEMP=p.LAT0+Y/(p.A*p.KS0);
        const double H=std::cos(TEMP);
        const double CON=std::sqrt((1.0-H*H)/(1.0+G*G));
        lat_rad=asinz0(CON);
        if(TEMP<0.0)lat_rad=-lat_rad;
        lon_rad=(G!=0.0||H!=0.0)?adjlz0(std::atan2(G,H)+p.LON0):p.LON0;
        return;
    }
    // Newton iteration on the meridional arc, tolerance 1e-10, max 6 steps.
    const double CON=(p.ML0+Y/p.KS0)/p.A;
    double PHI=CON;
    for(int i=0;i<6;++i) {
        const double DPHI=((CON+p.E1*std::sin(2.0*PHI)-p.E2*std::sin(4.0*PHI)
                            +p.E3*std::sin(6.0*PHI))/p.E0)-PHI;
        PHI=PHI+DPHI;
        if(std::fabs(DPHI)<=1.0e-10)break;
    }
    if(std::fabs(PHI)>=1.5707963267948966) { // >= HALFPI: polar point
        lat_rad=std::copysign(1.5707963267948966,Y);
        lon_rad=p.LON0;
        return;
    }
    const double SINPHI=std::sin(PHI);
    const double COSPHI=std::cos(PHI);
    const double TANPHI=std::tan(PHI);
    const double C=p.ESP*COSPHI*COSPHI;
    const double CS=C*C;
    const double T=TANPHI*TANPHI;
    const double TS=T*T;
    const double C2=1.0-p.ES*SINPHI*SINPHI;
    const double N=p.A/std::sqrt(C2);
    const double R=N*(1.0-p.ES)/C2;
    const double D=X/(N*p.KS0);
    const double DS=D*D;
    lat_rad=PHI-(N*TANPHI*DS/R)*(0.5-DS/24.0*(5.0+3.0*T+10.0*C-4.0*CS-9.0*p.ESP
            -DS/30.0*(61.0+90.0*T+298.0*C+45.0*TS-252.0*p.ESP-3.0*CS)));
    lon_rad=adjlz0(p.LON0+D*(1.0-DS/6.0*(1.0+2.0*T+C-DS/20.0*
            (5.0-2.0*C+28.0*T-3.0*CS+8.0*p.ESP+24.0*TS)))/COSPHI);
}
// GRID-cell-centre coordinate helper equivalent to one MICROI `GLOBE` call:
// easting/northing in metres -> N.latitude / E.longitude in degrees, using
// COORDLIB's own radians->degrees factor. Returns doubles; the caller rounds
// to REAL*4 the way `GLOBE`'s `SNGL(xyzio(...))` does.
inline void utm_north_to_latlon_deg(const UtmProjection& p,
                                    double easting_m,double northing_m,
                                    double& lat_deg,double& lon_deg) {
    double lon_rad=0.0,lat_rad=0.0;
    pj09z0_inverse(p,easting_m,northing_m,lon_rad,lat_rad);
    lat_deg=coordlib_detail::kGctpRadToDeg*lat_rad;
    lon_deg=coordlib_detail::kGctpRadToDeg*lon_rad;
}
} // namespace cteas::p6e
