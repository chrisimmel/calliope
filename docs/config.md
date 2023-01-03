# Sparrows
A Sparrow is an individual Calliope client, either a device or an application. It is
identified by a unique `client_id` passed with each request to the `/frames/` API.
The primary family of sparrows are implemented on ESP32-based hardware devices,
discussed in detail at [ESP32-Sparrow](https://github.com/mikalhart/ESP32-Sparrow).
Another example of a Calliope client/sparrow is
[Clio](https://github.com/chrisimmel/calliope/tree/main/docs/Clio.md), which runs
as a JavaScript app in a Web browser.

A configuration can be stored with the Calliope server to determine the default
treatment of a given sparrow in terms of the parameters that will be used by
default when serving `/v1/frames/` requests from that client. Everything about
how Calliope serves frames to a given sparrow is determined by the parameters
given with the request--configuration lets default values for these parameters
be stored for automatic use.

# Flocks
Sparrows can be collected into _flocks_, where a flock is a group of sparrows
with some shared configuration. Flocks can also be collected into flocks. A
sparrow or flock with a parent flock inherits default parameters, schedule, and
keys from its parent, making it possible to set up a tree of cascading options
to control the configuration of all sparrows.

# Configuration
A sparrow or flock configuration consists of the following:

* `id`: The ID of the sparrow or flock.
* `parent_flock_id`: The ID of the flock to which the sparrow or flock belongs,
if any. A sparrow or flock inherits the parameters and schedule of its parent
flock as defaults,
* `parameters`: Optional parameters to be passed through the flock inheritance
sequence to the strategy.
* `schedule`: An optional schedule to follow. For details, see
[Scheduling](https://github.com/chrisimmel/calliope/tree/main/docs/scheduling.md).
* `keys`: An optional dictionary of things like API keys. Overriding these
enables independent API tracking, management, and billing by sparrow or flock.