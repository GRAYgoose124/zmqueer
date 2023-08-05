# ZMQER

This is a simple python package that uses the [pyzmq](
https://pyzmq.readthedocs.io/en/latest/) library to create a number of peers on disjoint networks which can coalesce through a planned internet `Lighthouse`.

Design was stream of conscious, issues are encouraged.

# Peer hierarchy
As follows:

[`RandomPeer(JsonPeer)`](https://github.com/GRAYgoose124/codespace_play/blob/main/zmqer/zmqer/peer/group/json.py#L38) <- [`JsonPeer(WorkloadPeer)`](https://github.com/GRAYgoose124/codespace_play/blob/main/zmqer/zmqer/peer/group/json.py#L11) <- [`WorkloadPeer(GroupPeer)`](https://github.com/GRAYgoose124/codespace_play/blob/main/zmqer/zmqer/peer/group/workload.py#L8) <- [`GroupPeer(Peer)`](https://github.com/GRAYgoose124/codespace_play/blob/main/zmqer/zmqer/peer/group/__main__.py#L10) <- [`Peer(ABC)`](https://github.com/GRAYgoose124/codespace_play/blob/main/zmqer/zmqer/peer/__main__.py#L9)
### RandomPeer
`RandomPeer(JsonPeer)` is a high level example of how to use the `JsonPeer` and `WorkloadPeer` classes as ABC bases.

- At the [Workload](https://github.com/GRAYgoose124/codespace_play/blob/main/zmqer/zmqer/peer/group/workload.py#L18) level, the `async workload_wrapper` coroutine abstractmethod must be implemented as well as `handle_workload`. These implmentations can be seen in `JsonPeer` and `RandomPeer` respectively.

- `RandomPeer` is able to use it's methods `handle_work` and `workload` to create simple syncronous workloads which are asynchronously handled.

- `GroupPeer` itself leaves the abstract method [`broadcast_loop`](https://github.com/GRAYgoose124/codespace_play/blob/main/zmqer/zmqer/peer/__main__.py#L51) from `Peer(ABC)` to be implemented. This is overridden in [`WorkloadPeer`](https://github.com/GRAYgoose124/codespace_play/blob/main/zmqer/zmqer/peer/group/workload.py#L23).
## Installation
    $ poetry install
## Usage
    $ zmqer --help
```
usage: zmqer [-h] [-lt {stdout,file,None}] [-v {DEBUG,INFO,WARNING,ERROR,CRITICAL,v}] [-la] [-psd PEER_SETUP_DELAY] [-n N_PEERS] [-nl N_LATE_START_PEERS] [-sp STARTING_PORT]

options:
  -h, --help            show this help message and exit
  -lt {stdout,file,None}, --log-to {stdout,file,None}
                        Where to log output.
  -v {DEBUG,INFO,WARNING,ERROR,CRITICAL,v}, --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL,v}
                        Logging level
  -la, --log-all        Log all messages, not just those from specified logging peers.
  -psd PEER_SETUP_DELAY, --peer-setup-delay PEER_SETUP_DELAY
                        Delay in seconds before setting up late-start peers.
  -n N_PEERS, --n-peers N_PEERS
                        Number of peers to instantiate.
  -nl N_LATE_START_PEERS, --n-late-start-peers N_LATE_START_PEERS
                        Number of late-start peers to instantiate as a percentage of n_peers.
  -sp STARTING_PORT, --starting-port STARTING_PORT
                        Starting port for peer addresses.
```
### Try:
    $ zmqer -vv

    or if you would like to thrash your file system:

    $ zmqer -vv -la -lt file