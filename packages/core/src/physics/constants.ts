/**
 * Physical & orbital constants used across Short Gravity's
 * propagation, coverage, and line-of-sight calculations.
 */

/** Mean equatorial radius of Earth in kilometers (WGS-84). */
export const EARTH_RADIUS_KM = 6371;

/** Scene-scale factor: 1 Three.js unit = 1000 km. */
export const SCALE_FACTOR = 1 / 1000;

/** Degrees → radians. */
export const DEG_TO_RAD = Math.PI / 180;

/** Radians → degrees. */
export const RAD_TO_DEG = 180 / Math.PI;

/** Standard gravitational parameter of Earth (km³/s²). */
export const GM_EARTH = 398600.4418;

/** Earth's rotation rate in degrees per second (360° / 86164.1 s). */
export const EARTH_ROTATION_DEG_PER_SEC = 360 / 86164.1;

/** Sidereal day in seconds. */
export const SIDEREAL_DAY_S = 86164.1;

/** LEO orbit boundary altitude in km. */
export const LEO_MAX_ALT_KM = 2000;

/** Typical AST SpaceMobile BW3 orbit altitude in km. */
export const AST_NOMINAL_ALT_KM = 735;
