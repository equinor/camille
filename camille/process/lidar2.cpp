#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <cmath>
#include <tuple>
#include <limits>

namespace py = pybind11;

double sample_hgt( double hub_hgt,
                   double lidar_hgt,
                   double dist,
                   double pitch,
                   double roll,
                   double azm,
                   double zn ) {
    auto scale = sin(zn) * cos(pitch) * sin(azm - roll) + cos(zn) * sin(pitch);
    return hub_hgt + lidar_hgt + (dist / cos(zn)) * scale;
}

std::vector<double> planar_windspeed( double rws_a,
                                      double rws_b,
                                      double pitch,
                                      double roll,
                                      double azm_a,
                                      double azm_b,
                                      double zn_a,
                                      double zn_b ){
    auto a = cos(pitch) * cos(zn_a) +
             cos(azm_a) * sin(pitch) * sin(roll) * sin(zn_a) -
             cos(roll) * sin(pitch) * sin(zn_a) * sin(azm_a);

    auto b =
        cos(roll) * cos(azm_a) * sin(zn_a) + sin(roll) * sin(zn_a) * sin(azm_a);

    auto c = cos(pitch) * cos(zn_b) +
             cos(azm_b) * sin(pitch) * sin(roll) * sin(zn_b) -
             cos(roll) * sin(pitch) * sin(zn_b) * sin(azm_b);

    auto d =
        cos(roll) * cos(azm_b) * sin(zn_b) + sin(roll) * sin(zn_b) * sin(azm_b);

    auto x = (b * rws_b - d * rws_a) / (b * c - d * a);
    auto y = (rws_a - a * x) / b;

    return { sqrt(pow(x, 2) + pow(y, 2)), x, y };
}

double shear( double ws_upr,
              double ws_lwr,
              double hgt_upr,
              double hgt_lwr) {

    return log(ws_upr / ws_lwr) / log(hgt_upr / hgt_lwr);
}

double veer( double dir_upr,
             double dir_lwr,
             double hgt_upr,
             double hgt_lwr ) {

    return (dir_upr - dir_lwr) / (hgt_upr - hgt_lwr);
}

double extrapolate_windspeed( double hgt,
                              double shr,
                              double ref_windspeed,
                              double ref_hgt ) {

    return ref_windspeed * pow(hgt / ref_hgt, shr);
}

double extrapolate_wind_direction( double hgt,
                                   double vr,
                                   double ref_wind_direction,
                                   double ref_hgt) {
    return ref_wind_direction + vr * (hgt - ref_hgt);
}

std::vector<double> horiz_windspeed( const double* pitch,
                                     const double* roll,
                                     const double* rws,
                                     double dist,
                                     double hub_hgt,
                                     double lidar_hgt,
                                     const double* azimuths,
                                     const double* zeniths ) {

    /* Horizontal wind speed at nacelle hub height
     */

    const auto pitch_upr = (pitch[0] + pitch[1]) / 2.0;
    const auto pitch_lwr = (pitch[2] + pitch[3]) / 2.0;
    const auto roll_upr  = (roll[0]  + roll[1])  / 2.0;
    const auto roll_lwr  = (roll[2]  + roll[3])  / 2.0;

    std::vector<double> beam_hgts(4);

    for( int i = 0; i < 4; ++i )
        beam_hgts[i] = sample_hgt( hub_hgt, lidar_hgt, dist,
                                   pitch[i], roll[i],
                                   azimuths[i], zeniths[i] );

    const auto hgt_upr = (beam_hgts[0] + beam_hgts[1]) * 0.5;
    const auto hgt_lwr = (beam_hgts[2] + beam_hgts[3]) * 0.5;

    auto bellow_zero = [](double x){ return x < 0; };

    if( std::any_of(beam_hgts.begin(), beam_hgts.end(), bellow_zero) )
        throw std::invalid_argument("One or more beams are under ground/water.");

    const auto ws_upr = planar_windspeed( rws[0], rws[1], pitch_upr, roll_upr,
                                          azimuths[0],azimuths[1], zeniths[0],
                                          zeniths[1] );
    const auto ws_lwr = planar_windspeed( rws[2], rws[3], pitch_lwr, roll_lwr,
                                          azimuths[2],azimuths[3], zeniths[2],
                                          zeniths[3] );

    const auto dir_upr = atan2(ws_upr[2], ws_upr[1]);
    const auto dir_lwr = atan2(ws_lwr[2], ws_lwr[1]);

    const auto shr = shear(ws_upr[0], ws_lwr[0], hgt_upr, hgt_lwr);
    const auto vr = veer(dir_upr, dir_lwr, hgt_upr, hgt_lwr);

    const auto hws = extrapolate_windspeed(hub_hgt, shr, ws_lwr[0], hgt_lwr);
    const auto hwd = extrapolate_wind_direction(hub_hgt, vr, dir_lwr, hgt_lwr);

    return {hws, hwd, shr, vr, ws_upr[0], ws_lwr[0]};
}

using ps_result_type = std::tuple< py::array_t<double>, py::array_t<double>,
                                   py::array_t<double>, py::array_t<double>,
                                   py::array_t<double>, py::array_t<double> >;

ps_result_type ps( py::array_t<std::int64_t> _time,
                   py::array_t<int> _los_id,
                   py::array_t<double> _pitch,
                   py::array_t<double> _roll,
                   py::array_t<double> _radial_windspeed,
                   py::array_t<double> _status,
                   const double dist,
                   const double hub_hgt,
                   const double lidar_hgt,
                   py::array_t<double> _azimuths,
                   py::array_t<double> _zeniths ) {

    auto _timeInfo             = _time.request();
    auto _los_idInfo           = _los_id.request();
    auto _pitchInfo            = _pitch.request();
    auto _rollInfo             = _roll.request();
    auto _radial_windspeedInfo = _radial_windspeed.request();
    auto _statusInfo           = _status.request();
    auto _azimuthsInfo         = _azimuths.request();
    auto _zenithsInfo          = _zeniths.request();

    bool sizes_equal =   _timeInfo.size  == _pitchInfo.size
                     and _pitchInfo.size == _rollInfo.size
                     and _rollInfo.size  == _radial_windspeedInfo.size;

    if( not sizes_equal )
        throw std::invalid_argument("All sizes must be the same.");

    std::size_t size = _los_idInfo.size;

    auto time             = _time.data();
    auto los_id           = _los_id.data();
    auto pitch            = _pitch.data();
    auto roll             = _roll.data();
    auto radial_windspeed = _radial_windspeed.data();
    auto status           = _status.data();
    auto azimuths         = _azimuths.data();
    auto zeniths          = _zeniths.data();

    py::array_t<double> _hws(size);
    py::array_t<double> _hwd(size);
    py::array_t<double> _shear(size);
    py::array_t<double> _veer(size);
    py::array_t<double> _ws_upper(size);
    py::array_t<double> _ws_lower(size);

    auto hws = _hws.mutable_data();
    auto hwd = _hwd.mutable_data();
    auto shear = _shear.mutable_data();
    auto veer = _veer.mutable_data();
    auto ws_upper = _ws_upper.mutable_data();
    auto ws_lower = _ws_lower.mutable_data();

    auto predicate = [&](std::size_t i) {
        bool oredered_los_id =   los_id[i]   ==   0
                             and los_id[i+1] ==   1
                             and los_id[i+2] ==   2
                             and los_id[i+3] ==   3;

        bool status_ok =   status[i]   == 1.0
                       and status[i+1] == 1.0
                       and status[i+2] == 1.0
                       and status[i+3] == 1.0;

        auto max_time = *std::max_element((time + i), (time + i + 4));
        auto min_time = *std::min_element((time + i), (time + i + 4));

        bool duration_ok = max_time - min_time < 5 * 1e9;

        return oredered_los_id and status_ok and duration_ok;
    };

    for (std::size_t i = 0; i < size; ++i ) {
        if( i > size - 4 or !predicate(i) ) {
            double NaN = std::numeric_limits<double>::quiet_NaN();
            hws[i] = hwd[i] = shear[i] = NaN;
            veer[i] = ws_upper[i] = ws_lower[i] = NaN;
            continue;
        }
        auto res = horiz_windspeed( &pitch[i], &roll[i], &radial_windspeed[i],
                                    dist, hub_hgt, lidar_hgt,
                                    azimuths, zeniths );
        hws[i] = res[0];
        hwd[i] = res[1];
        shear[i] = res[2];
        veer[i] = res[3];
        ws_upper[i] = res[4];
        ws_lower[i] = res[5];
    }

    return std::make_tuple( _hws, _hwd, _shear, _veer, _ws_upper, _ws_lower );
}

PYBIND11_MODULE(lidar2extension, m) {
    m.def("sample_hgt", &sample_hgt,
          "      Sample height\n"
          "\n"
          "      Parameters\n"
          "      ----------\n"
          "      hub_hgt : float\n"
          "          Nacelle hub height\n"
          "      lidar_hgt : float\n"
          "          Height of the LiDAR\n"
          "      dist : float\n"
          "          Measurement distance\n"
          "      pitch : float\n"
          "      roll : float\n"
          "      azm : float\n"
          "          Line-of-sight azimuth\n"
          "      zn : float\n"
          "          Line-of-sight zenith\n"
          "\n"
          "      Returns\n"
          "      -------\n"
          "      float\n"
          "          Height of the beam for line-of-sight `i` at distance `dist`"
    );

    m.def("planar_windspeed", &planar_windspeed,
          "   Planar windspeed\n"
          "\n"
          "    Calculates the wind speed for a horizontal plane given two beams, a and b. a\n"
          "    being the leftmost beam  and b the  rightmost as seen from behind the LiDAR.\n"
          "    The  vector and  orientation  of  the  beams are  given  by the pitch, roll,\n"
          "    zeniths  and azimuths. Measured wind speeds are  given as  radial wind speed\n"
          "    (RWS), that is the actual wind vector as projected onto the beam vector. The\n"
          "    calculation is done by solving the following equations for V, where V is the\n"
          "    wind vector:\n"
          "\n"
          "    RWSa = R . La . V\n"
          "    RWSb = R . Lb . V\n"
          "\n"
          "    R is  the rotational  matrix Ry(pitch)  .  Rx(roll),  and  L are the LOS, or\n"
          "    Line-Of-Sights, for beam a and b. The beam vector (RL) is given by:\n"
          "\n"
          "                        Ry(p)                 Rx(r)                 L\n"
          "                 | cos p  0  -sin p | | 1    0       0   | |      cos zn      |\n"
          "    RL = R . L = |   0    1    0    | | 0  cos r   sin r | | sin zn * cos azm |\n"
          "                 | sin p  0  cos p  | | 0  -sin r  cos r | | sin zn * sin azm |\n"
          "\n"
          "    Because the wind speed is projected onto the beam, RL, we have:\n"
          "\n"
          "               | Vx |\n"
          "    RWS = RL . | Vy |\n"
          "               | Vz |\n"
          "\n"
          "    If we assume Vz to be 0, we get:\n"
          "\n"
          "    RWSa = RLa_x * Vx + RLa_y * Vy\n"
          "         = a * Vx + b * Vy\n"
          "    RWSb = RLb_x * Vx + RLb_y * Vy\n"
          "         = c * Vx + d * Vy\n"
          "\n"
          "    Note that we rename RLa_x, RLa_y, RLb_x, and RLb_y to a, b, c, and d.\n"
          "\n"
          "    Solving for Vx and Vy gives us:\n"
          "\n"
          "    Vx = (b * RWSb - d * RWSa) / (b * c - d * a)\n"
          "    Vy = (RWSa - a * Vx) / b\n"
          "\n"
          "    The coordinate system is left-handed, X-forward, Y-right and Z-up.\n"
          "\n"
          "    Parameters\n"
          "    ----------\n"
          "    rws_a : float\n"
          "        Measured radial wind speed a\n"
          "    rws_b : float\n"
          "        Measured radial wind speed b\n"
          "    pitch : float\n"
          "    roll : float\n"
          "    azm_a : float\n"
          "        Line-of-sight a azimuth\n"
          "    azm_b : float\n"
          "        Line-of-sight b azimuth\n"
          "    zn_a : float\n"
          "        Line-of-sight a zenith\n"
          "    zn_b : float\n"
          "        Line-of-sight b zenith\n"
          "\n"
          "    Returns\n"
          "    -------\n"
          "    float\n"
          "        Planar wind speed reconstructed from rws_a and rws_b\n"
    );

    m.def("shear", &shear,
          "    Shear\n"
          "\n"
          "    Calculate shear\n"
          "\n"
          "    Parameters\n"
          "    ----------\n"
          "    ws_upr : float\n"
          "        Wind speed of the upper plane\n"
          "    ws_lwr : float\n"
          "        Wind speed of the lower plane\n"
          "    hgt_upr : float\n"
          "        Height of the upper plane\n"
          "    hgt_lwr : float\n"
          "        Height of the lower plane\n"
          "\n"
          "    Returns\n"
          "    -------\n"
          "    float\n"
          "        Shear\n"
          "\n"
          "    References\n"
          "    ----------\n"
          "\n"
          "    .. [1] https://en.wikipedia.org/wiki/Wind_profile_power_law\n"
    );

    m.def("veer", &veer,
          "   Veer\n"
          "\n"
          "    Calculate vertical wind veer from horizontal directions\n"
          "\n"
          "    Parameters\n"
          "    ----------\n"
          "    dir_upr : float\n"
          "        Wind direction in the upper plane\n"
          "    dir_lwr : float\n"
          "        Wind direction in the lower plane\n"
          "    hgt_upr : float\n"
          "        Height of the upper plane\n"
          "    hgt_lwr : float\n"
          "        Height of the lower plane\n"
          "\n"
          "    Returns\n"
          "    -------\n"
          "    float\n"
          "        Veer\n"
    );

    m.def("extrapolate_windspeed", &extrapolate_windspeed,
          "    Extrapolate windspeed\n"
          "\n"
          "    Extrapolate windspeed using the wind profile power law [1]_.\n"
          "\n"
          "    Parameters\n"
          "    ----------\n"
          "    hgt : float\n"
          "        Target height\n"
          "    shr : float\n"
          "        Shear\n"
          "    ref_windspeed : float\n"
          "        Reference wind speed\n"
          "    ref_hgt : float\n"
          "        Reference height\n"
          "\n"
          "    Returns\n"
          "    -------\n"
          "    float\n"
          "        Wind speed at target height\n"
          "\n"
          "    References\n"
          "    ----------\n"
          "\n"
          "    .. [1] https://en.wikipedia.org/wiki/Wind_profile_power_law\n"
    );

    m.def("extrapolate_wind_direction", &extrapolate_wind_direction,
          "    Extrapolate wind direction\n"
          "\n"
          "    Extrapolate wind direction using the linear law and veer\n"
          "\n"
          "    Parameters\n"
          "    ----------\n"
          "    hgt : float\n"
          "        Target height\n"
          "    vr : float\n"
          "        Vertical wind veer\n"
          "    ref_wind_direction : float\n"
          "        Reference wind direction\n"
          "    ref_hgt : float\n"
          "        Reference height\n"
          "\n"
          "    Returns\n"
          "    -------\n"
          "    float\n"
          "        Wind direction at target height\n"
    );

    m.def("ps", &ps, "process");
}
