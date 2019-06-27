#include <cmath>
#include <functional>
#include <tuple>
#include <utility>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

namespace py = pybind11;

static const auto dense = py::array::c_style | py::array::forcecast;

namespace {
namespace lidar {

struct sample {
    std::uint64_t time;
    int los_id;
    double rws;
    double pitch;
    double roll;
    int status;
};

struct planar_desc {
    int status;
    double spd;
    double dir;
    double x;
    double y;
    double hgt;
};

struct windfield_desc {
    std::uint64_t time;
    double shear;
    double veer;
    planar_desc upper;
    planar_desc lower;

    std::uint64_t get_time() const noexcept { return time; }
    double get_shear()       const noexcept { return shear; }
    double get_veer()        const noexcept { return veer; }
    double get_status_upr()  const noexcept { return upper.status; }
    double get_status_lwr()  const noexcept { return lower.status; }
    double get_spd_upr()     const noexcept { return upper.spd; }
    double get_spd_lwr()     const noexcept { return lower.spd; }
    double get_dir_upr()     const noexcept { return upper.dir; }
    double get_dir_lwr()     const noexcept { return lower.dir; }
    double get_x_upr()       const noexcept { return upper.x; }
    double get_x_lwr()       const noexcept { return lower.x; }
    double get_y_upr()       const noexcept { return upper.y; }
    double get_y_lwr()       const noexcept { return lower.y; }
    double get_hgt_upr()     const noexcept { return upper.hgt; }
    double get_hgt_lwr()     const noexcept { return lower.hgt; }
};

static const auto sample_hgt_docstring = R"(
Parameters
----------
hub_hgt : float
    Nacelle hub height
lidar_hgt : float
    Height of the LiDAR
dist : float
    Measurement distance
pitch : float
roll : float
azm : float
    Line-of-sight azimuth
zn : float
    Line-of-sight zenith

Returns
-------
float
    Height of the beam at distance `dist`
)";

double sample_hgt(double lidar_hgt,
                  double dist,
                  double pitch,
                  double roll,
                  double azm,
                  double zn) noexcept {
    using std::sin;
    using std::cos;

    // double scale = (cos(zn) * sin(pitch) +
    //                -sin(zn) * cos(azm) * cos(pitch) * sin(roll) +
    //                 sin(zn) * sin(azm) * cos(pitch) * cos(roll));
    // The above collapsed to this:
    double magic = azm - roll;
    double scale = sin(zn) * cos(pitch) * sin(magic) + cos(zn) * sin(pitch);
    return lidar_hgt + (dist / cos(zn)) * scale;
}

static const auto shear_docstring = R"(
Calculate shear

Parameters
----------
ws_upr : float
    Wind speed of the upper plane
ws_lwr : float
    Wind speed of the lower plane
hgt_upr : float
    Height of the upper plane
hgt_lwr : float
    Height of the lower plane

Returns
-------
float
    Shear

References
----------

.. [1] https://en.wikipedia.org/wiki/Wind_profile_power_law
)";

double shear(double ws_upr,
             double ws_lwr,
             double hgt_upr,
             double hgt_lwr) noexcept {
    using std::log;
    return log(ws_upr / ws_lwr) / log(hgt_upr / hgt_lwr);
}

static const auto veer_docstring = R"(
Calculate vertical wind veer from horizontal directions

Parameters
----------
dir_upr : float
    Wind direction in the upper plane
dir_lwr : float
    Wind direction in the lower plane
hgt_upr : float
    Height of the upper plane
hgt_lwr : float
    Height of the lower plane

Returns
-------
float
    Veer
)";

double veer(double dir_upr,
            double dir_lwr,
            double hgt_upr,
            double hgt_lwr) noexcept {
    return (dir_upr - dir_lwr) / (hgt_upr - hgt_lwr);
}

static const auto planar_windspeed_docstring = R"(
Calculates the wind speed for a horizontal plane given two beams, a and b. a
being the leftmost beam  and b the  rightmost as seen from behind the LiDAR.
The  vector and  orientation  of  the  beams are  given  by the pitch, roll,
zeniths  and azimuths. Measured wind speeds are  given as  radial wind speed
(RWS), that is the actual wind vector as projected onto the beam vector. The
calculation is done by solving the following equations for V, where V is the
wind vector:

RWSa = R . La . V
RWSb = R . Lb . V

R is  the rotational  matrix Ry(pitch)  .  Rx(roll),  and  L are the LOS, or
Line-Of-Sights, for beam a and b. The beam vector (RL) is given by:

                    Ry(p)                 Rx(r)                 L
             | cos p  0  -sin p | | 1    0       0   | |      cos zn      |
RL = R . L = |   0    1    0    | | 0  cos r   sin r | | sin zn * cos azm |
             | sin p  0  cos p  | | 0  -sin r  cos r | | sin zn * sin azm |

Because the wind speed is projected onto the beam, RL, we have:

           | Vx |
RWS = RL . | Vy |
           | Vz |

If we assume Vz to be 0, we get:

RWSa = RLa_x * Vx + RLa_y * Vy
     = a * Vx + b * Vy
RWSb = RLb_x * Vx + RLb_y * Vy
     = c * Vx + d * Vy

Note that we rename RLa_x, RLa_y, RLb_x, and RLb_y to a, b, c, and d.

Solving for Vx and Vy gives us:

Vx = (b * RWSb - d * RWSa) / (b * c - d * a)
Vy = (RWSa - a * Vx) / b

The coordinate system is left-handed, X-forward, Y-right and Z-up.

Parameters
----------
rws_a : float
    Measured radial wind speed a
rws_b : float
    Measured radial wind speed b
pitch : float
roll : float
azm_a : float
    Line-of-sight a azimuth
azm_b : float
    Line-of-sight b azimuth
zn_a : float
    Line-of-sight a zenith
zn_b : float
    Line-of-sight b zenith

Returns
-------
float
    Planar wind speed reconstructed from rws_a and rws_b
)";

std::tuple<double, double> planar_windspeed(double rws_a,
                                            double rws_b,
                                            double pitch,
                                            double roll,
                                            double azm_a,
                                            double azm_b,
                                            double zn_a,
                                            double zn_b) noexcept {
    using std::sin;
    using std::cos;

    double a = cos(pitch) * cos(zn_a) +
               cos(azm_a) * sin(pitch) * sin(roll) * sin(zn_a) -
               cos(roll)  * sin(pitch) * sin(zn_a) * sin(azm_a);

    double b = cos(roll) * cos(azm_a) * sin(zn_a) +
               sin(roll) * sin(zn_a)  * sin(azm_a);

    double c = cos(pitch) * cos(zn_b) +
               cos(azm_b) * sin(pitch) * sin(roll) * sin(zn_b) -
               cos(roll)  * sin(pitch) * sin(zn_b) * sin(azm_b);

    double d = cos(roll) * cos(azm_b) * sin(zn_b) +
               sin(roll) * sin(zn_b) * sin(azm_b);

    double x = (b * rws_b - d * rws_a) / (b * c - d * a);
    double y = (rws_a - a * x) / b;

    return std::make_tuple(x, y);
}

planar_desc calc_plane_desc(const sample& beam_a,
                            const sample& beam_b,
                            const double dist,
                            const double lidar_hgt,
                            const double azm_a,
                            const double azm_b,
                            const double zn_a,
                            const double zn_b) noexcept {
    using std::sqrt;
    using std::atan2;

    planar_desc desc;

    desc.status = beam_a.status != 0 && beam_b.status != 0 ? 1 : 0;
    if (desc.status == 0) {
        desc.spd = std::nan("");
        desc.dir = std::nan("");
        desc.x = std::nan("");
        desc.y = std::nan("");
        desc.spd = std::nan("");

        return desc;
    }

    double pitch = (beam_a.pitch + beam_b.pitch) / 2.0;
    double roll = (beam_a.roll + beam_b.roll) / 2.0;

    double hgt_a = sample_hgt(lidar_hgt, dist, pitch, roll, azm_a, zn_a);
    double hgt_b = sample_hgt(lidar_hgt, dist, pitch, roll, azm_b, zn_b);
    double hgt = (hgt_a + hgt_b) / 2.0;

    auto vec = planar_windspeed(
        beam_a.rws, beam_b.rws, pitch, roll, azm_a, azm_b, zn_a, zn_b);

    double x = std::get<0>(vec);
    double y = std::get<1>(vec);
    double speed = sqrt(x * x + y * y);
    double dir = atan2(y / speed, x / speed);

    desc.spd = speed;
    desc.dir = dir;
    desc.x = x;
    desc.y = y;
    desc.hgt = hgt;
    return desc;
}

windfield_desc calc_windfield_desc(
        const std::uint64_t time,
        const std::array<sample, 4>& beam,
        const double distance,
        const double lidar_hgt,
        const std::array<double, 4>& azimuths,
        const std::array<double, 4>& zeniths) noexcept {
    planar_desc upper_desc = calc_plane_desc(
        beam[0], beam[1],
        distance, lidar_hgt,
        azimuths[0], azimuths[1],
        zeniths[0], zeniths[1]);
    planar_desc lower_desc = calc_plane_desc(
        beam[2], beam[3],
        distance, lidar_hgt,
        azimuths[2], azimuths[3],
        zeniths[2], zeniths[3]);

    windfield_desc wf_desc;
    wf_desc.time = time;
    wf_desc.shear = std::nan("");
    wf_desc.veer = std::nan("");
    wf_desc.upper = std::move(upper_desc);
    wf_desc.lower = std::move(lower_desc);

    if (wf_desc.upper.status == 1 && wf_desc.lower.status == 1) {
        wf_desc.shear = shear(wf_desc.upper.spd, wf_desc.lower.spd,
                              wf_desc.upper.hgt, wf_desc.lower.hgt);
        wf_desc.veer = veer(wf_desc.upper.dir, wf_desc.lower.dir,
                            wf_desc.upper.hgt, wf_desc.lower.hgt);
    }

    return wf_desc;
}

template<typename T>
T* checked_ptr(py::array_t<T, dense>& in,
               const ssize_t expected_ndim,
               const std::vector<ssize_t>& expected_shape) {
    const auto desc = in.request();

    if (desc.ndim != expected_ndim) {
        std::string msg = "Lengths of all columns must be the same";
        throw std::invalid_argument(msg);
    }

    if (desc.shape != expected_shape) {
        std::string msg = "All columns must be one dimensional";
        throw std::invalid_argument(msg);
    }

    return static_cast< T* >(desc.ptr);
}

bool create_window(const std::array<sample, 4>& b,
                   std::array<sample, 4>& win) noexcept {
    auto valid_los_id = [](const sample& s){
        return 0 <= s.los_id && s.los_id < 4;
    };
    if (!std::all_of(std::begin(b), std::end(b), valid_los_id)) {
        return false;
    }

    std::array<bool, 4> found = {};
    for (int i = 0; i < 4; i++) {
        found[b[i].los_id] = true;
    }

    if (!found[0] || !found[1] || !found[2] || !found[3]) {
        return false;
    }

    win[b[0].los_id] = b[0];
    win[b[1].los_id] = b[1];
    win[b[2].los_id] = b[2];
    win[b[3].los_id] = b[3];

    return true;
}

template<typename F>
auto mkcol(F fn, const std::vector<windfield_desc>& wf_descs) noexcept
        -> py::array_t< decltype(fn(wf_descs.front())), dense > {
    /*
     * Populates a numpy array all instances of one member of the
     * windfield_descs in wf_descs
     */

    // Figure out the return type of this function, and the array element type
    using return_type = decltype(mkcol(fn, wf_descs));
    using T = typename return_type::value_type;

    auto arr = return_type(wf_descs.size());
    auto desc = arr.request();
    auto ptr = static_cast<T*>(desc.ptr);
    for (int i = 0; i < wf_descs.size(); i++) {
        ptr[i] = fn(wf_descs[i]);
    }
    return arr;
}

py::dict core_windfield_desc(py::array_t<std::uint64_t, dense> time,
                             py::array_t<int, dense> los_id,
                             py::array_t<double, dense> rws,
                             py::array_t<double, dense> pitch,
                             py::array_t<double, dense> roll,
                             py::array_t<int, dense> status,
                             const double distance,
                             const double lidar_hgt,
                             const std::array<double, 4>& azimuths,
                             const std::array<double, 4>& zeniths) {
    auto time_desc = time.request();
    if (time_desc.ndim != 1)
        throw std::invalid_argument("Time column not one dimensional");
    auto len = time_desc.shape[0];

    const auto* timep   = static_cast< std::uint64_t* >(time_desc.ptr);
    const auto* los_idp = checked_ptr(los_id, 1, time_desc.shape);
    const auto* rwsp    = checked_ptr(rws,    1, time_desc.shape);
    const auto* pitchp  = checked_ptr(pitch,  1, time_desc.shape);
    const auto* rollp   = checked_ptr(roll,   1, time_desc.shape);
    const auto* statusp = checked_ptr(status, 1, time_desc.shape);

    std::vector<sample> beam(len);
    for (int i = 0; i < len; i ++) {
        beam[i].time   = timep[i];
        beam[i].los_id = los_idp[i];
        beam[i].rws    = rwsp[i];
        beam[i].pitch  = pitchp[i];
        beam[i].roll   = rollp[i];
        beam[i].status = statusp[i];
    }

    std::vector<windfield_desc> wf_descs;
    for (int i = 0; i < len - 3; i++) {
        const std::array<sample, 4> b = {
            beam[i], beam[i + 1], beam[i + 2], beam[i + 3],
        };

        const std::uint64_t time = b[0].time;

        std::array<sample, 4> window;
        if (!create_window(b, window)) {
            continue;
        }

        windfield_desc wf_desc = calc_windfield_desc(
            time, window, distance, lidar_hgt, azimuths, zeniths);

        if (wf_desc.upper.status == 1 || wf_desc.lower.status == 1) {
            wf_descs.push_back(wf_desc);
        }
    }

    using wfi = windfield_desc;
    auto d = py::dict();
    d["time"]       = mkcol(std::mem_fn(&wfi::get_time),       wf_descs);
    d["shear"]      = mkcol(std::mem_fn(&wfi::get_shear),      wf_descs);
    d["veer"]       = mkcol(std::mem_fn(&wfi::get_veer),       wf_descs);
    d["status_upr"] = mkcol(std::mem_fn(&wfi::get_status_upr), wf_descs);
    d["status_lwr"] = mkcol(std::mem_fn(&wfi::get_status_lwr), wf_descs);
    d["speed_upr"]  = mkcol(std::mem_fn(&wfi::get_spd_upr),    wf_descs);
    d["speed_lwr"]  = mkcol(std::mem_fn(&wfi::get_spd_lwr),    wf_descs);
    d["dir_upr"]    = mkcol(std::mem_fn(&wfi::get_dir_upr),    wf_descs);
    d["dir_lwr"]    = mkcol(std::mem_fn(&wfi::get_dir_lwr),    wf_descs);
    d["x_upr"]      = mkcol(std::mem_fn(&wfi::get_x_upr),      wf_descs);
    d["y_upr"]      = mkcol(std::mem_fn(&wfi::get_y_upr),      wf_descs);
    d["x_lwr"]      = mkcol(std::mem_fn(&wfi::get_x_lwr),      wf_descs);
    d["y_lwr"]      = mkcol(std::mem_fn(&wfi::get_y_lwr),      wf_descs);
    d["height_upr"] = mkcol(std::mem_fn(&wfi::get_hgt_upr),    wf_descs);
    d["height_lwr"] = mkcol(std::mem_fn(&wfi::get_hgt_lwr),    wf_descs);
    return d;
}

} // ^ namespace lidar
} // ^ anonymous namespace

PYBIND11_MODULE(core, m) {
    m.def("sample_hgt", lidar::sample_hgt,
                        lidar::sample_hgt_docstring);
    m.def("core_windfield_desc", lidar::core_windfield_desc);
}
