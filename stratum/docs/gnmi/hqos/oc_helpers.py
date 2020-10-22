
from st_bindings import openconfig_qos
import json

# Queue Info
num_tcs = 4         # Number of traffic classes per subscriber
num_subs = 6        # Number of subscribers
num_queues = num_tcs * (num_subs + 1)
q = {}              # queue map
next_qid = 0
first_qid = 0
last_qid = num_queues-1

# Scheduler Policy globals
intf_sp = {}            # Interface Sched Policies
intf_sched = {}         # Interface Schedulers
svg_sched = {}          # Service Group Schedulers
sub_sched = {}          # Subscriber Schedlers
sgsp_name = "sgsp"      # Service Group Scheduler Policy name
next_sched_seq = 0      # Next scheduler sequence number
ROOT_LEVEL = 0          # the root node level number

# Interfaces
intfs = {}         # Interface objects

# OpenConfig base class
ocq = openconfig_qos()

#------------------------ Queue Stuff ----------------------------

def add_drop_profile(name, type, max_q, minth=0, maxth=0, maxprob=0):
    """Add a new drop profile

    :param string    name: the drop profile name
    :param string    type: the queue type
    :param int      max_q: maximum queue size
    :param int      minth: minimum threshold for RED
    :param int      maxth: maximum threshold for RED
    :param int    maxprob: maximum probability for RED

    :return: returns the drop profile
    :rtype: drop_profile
    """

    dp = ocq.qos.drop_profiles.drop_profile.add(name)
    dp.config.queue_type = type
    dp.config.max_queue_depth_packets = max_q
    dp.red.config.minth = minth
    dp.red.config.maxth = maxth
    dp.red.config.maxprob = maxprob

    return dp

def setup_drop_profiles():
    """Setup the Drop Profiles for the QoS module"""

    # Setup Residential Subscriber Drop Profiles
    # Voice - tail drop profile
    add_drop_profile("voice", "DROP_TAIL", 20)

    # Data - RED drop profile
    add_drop_profile("data", "RED", 40, 10, 40, 60)

    # Video - RED drop profile
    add_drop_profile("video", "RED", 30, 20, 40, 70)

    return

def setup_queues():
    """Setup the QoS Queues"""

    for i in range(num_queues):
        name = "q"+str(i)
        q[i] = ocq.qos.queues.queue.add(name)
        q[i].config.name = name
        q[i].config.drop_profile = "data"

    return

def add_queue_to_sched(name, sched, weight, priority, dp_name):
    """Add a queue to the given scheduler

    :param string     name: traffic class name
    :param scheduler sched: scheduler object
    :param int      weight: weight
    :param int    priority: priority
    :param string  dp_name: drop profile name

    :return: returns the traffic class object
    :rtype: input object

    """

    global next_qid

    tc = sched.inputs.input.add(name)
    tc.config.input_type = "QUEUE"
    tc.config.queue = "q"+str(next_qid)
    tc.config.weight = weight
    tc.config.priority = priority
    q[next_qid].config.drop_profile = dp_name
    next_qid += 1

    return

def add_resi_queues(sched):
    """Add a residential queues to the given scheduler

    :param scheduler sched: scheduler object

    """

    add_queue_to_sched("voice", sched, 10, 0, "tc_0")
    add_queue_to_sched("data", sched, 20, 0, "tc_1")
    add_queue_to_sched("video", sched, 30, 0, "tc_2")
    add_queue_to_sched("other", sched, 40, 0, "tc_3")

    return

#------------------------ Scheduler Stuff ----------------------------

def add_scheduler_policy(name):
    """Add an scheduler policy

    :param string name: scheduler policy name

    :return: scheduler policy object
    
    """

    # Scheduler Policy
    sched_policy = ocq.qos.scheduler_policies.scheduler_policy.add(name)
    sched_policy.config.name = name

    return sched_policy

def add_scheduler(spol, name, level):
    """Add a scheduler to the scheduler policies

    :param scheduler_policy  spol:  scheduler policy
    :param string            name:  scheduler name
    :param uint8            level:  scheduler level (0 = root)

    :return:   returns the scheduler
    :rtype: scheduler object

    """

    global next_sched_seq

    sched = spol.schedulers.scheduler.add(next_sched_seq)
    sched.config.sequence = next_sched_seq
    sched.config.name = name
    sched.config.level = level

    # Increment the next scheduler sequenece number
    next_sched_seq += 1

    return sched

def add_child_scheduler(name, spol, osched, weight, priority):
    """Add a scheduler to the scheduler policies

    :param string            name:  scheduler name
    :param scheduler_policy  spol:  scheduler policy
    :param scheduler       osched:  output scheduler
    :param int             weight:  weight
    :param int           priority:  priority
    :return:   returns the scheduler
    :rtype: scheduler object

    """

    # Subsriber Scheduler
    sched = add_scheduler(spol, name, osched.config.level+1)
    sched.config.type = "ONE_RATE_TWO_COLOR"
    # sched.config.priority = "STRICT"
    sched.output.config.output_type = "SCHEDULER"

    # ptr from Output Scheduler to us
    inp = osched.inputs.input.add(name)
    inp.config.id = name
    inp.config.input_type = "IN_PROFILE"
    inp.config.weight = weight
    inp.config.priority = priority
    inp.config.input_scheduler = sched.sequence

    return sched

def set_1r2c_scheduler_config(sched, cir):
    """Set the one rate two colour config info

    :param int  cir: commited information rate in bps
    """

    sched.config.type = "ONE_RATE_TWO_COLOR"
    sched.one_rate_two_color.exceed_action.config.drop = True
    sched.one_rate_two_color.config.cir = cir
    sched.one_rate_two_color.config.queuing_behavior = "SHAPE"

    return

def set_2r3c_scheduler_config(sched, cir, pir):
    """Set the two rate three colour config info

    :param int  cir: commited information rate in bps
    :param int  pir: peak information rate in bps
    """

    sched.config.type = "TWO_RATE_THREE_COLOR"
    sched.two_rate_three_color.exceed_action.config.drop = True
    sched.two_rate_three_color.config.cir = cir
    sched.two_rate_three_color.config.pir = pir
    sched.two_rate_three_color.config.queuing_behavior = "SHAPE"

    return

def add_interface_scheduler(iname, spol):
    """Add a interface scheduler to the scheduler policies

    :param string           iname:  interface name
    :param scheduler_policy  spol:  scheduler policy
    :return:   returns the scheduler
    :rtype: scheduler object

    """

    # Subsriber Scheduler
    sched = add_scheduler(spol, iname, ROOT_LEVEL)
    sched.config.type = "ONE_RATE_TWO_COLOR"
    # sched.config.priority = "STRICT"
    sched.output.config.output_type = "INTERFACE"

    # set the last-scheduler leafref
    intf_sp[iname].config.root_scheduler = sched.sequence

    return sched

#------------------------ Scheduler Stuff ----------------------------

def setup_schedulers(iname):
    """Setup the HQoS schedulers on an interface

    :param string iname: interface name
    """

    # Add Interface Scheduler Policy & Scheduler
    intf_sp[iname] = add_scheduler_policy(iname)
    intf_sched[iname] = add_interface_scheduler(iname, intf_sp[iname])
    set_1r2c_scheduler_config(intf_sched[iname], 40000000000)

    # Add scheduler policy to the interface
    add_sched_policy_to_interface(iname, iname)

    return

def add_svg(iname, svg_name, weight, priority, cir):
    """Add Service Group

    :param string    iname: interface name
    :param string svg_name: service group name
    :param int      weight: weight for this scheduler
    :param int    priority: priority for this scheduler
    :param int         cir: committed information rate for this scheduler
    """

    # Add service group
    svg_sched[svg_name] = \
        add_child_scheduler(svg_name, intf_sp[iname], intf_sched[iname],
                            weight, priority)
    set_1r2c_scheduler_config(svg_sched[svg_name], cir)

    return

def add_sub(iname, svg_name, sub_name, weight, priority, cir):
    """Add a subscriber scheduler

    :param string    iname: interface name
    :param string svg_name: service group name
    :param string sub_name: subscriber name
    :param int      weight: weight for this scheduler
    :param int    priority: priority for this scheduler
    :param int         cir: committed information rate for this scheduler
    """

    # Add a subscriber
    sub_sched[sub_name] = \
        add_child_scheduler(sub_name, intf_sp[iname], 
                            svg_sched[svg_name], weight, priority)
    set_1r2c_scheduler_config(sub_sched[sub_name], cir)
    add_resi_queues(sub_sched[sub_name])

    return

def add_hqos(iname):
    """Add HQoS to an interface"""

    # Add Service Group 1
    svg_name = "svg1"
    add_svg(iname, svg_name, 10, 0, 40000000000)

    # Add subscribers for svg1
    add_sub(iname, svg_name, "sub1", 10, 0, 10000000)
    add_sub(iname, svg_name, "sub2", 20, 0, 10000000)
    add_sub(iname, svg_name, "sub3", 20, 0, 10000000)

    # Add Service Group 2
    svg_name = "svg2"
    add_svg(iname, svg_name, 10, 0, 50000000000)

    # Add subscribers for svg2
    add_sub(iname, svg_name, "sub4", 10, 0, 2000000)
    add_sub(iname, svg_name, "sub5", 10, 0, 2000000)

    # Add Service Group 3
    svg_name = "svg3"
    add_svg(iname, svg_name, 10, 0, 20000000000)

    # Add subscribers for svg3
    add_sub(iname, svg_name, "sub6", 10, 0, 10000000)

    return

def add_interface(name):
    """Add an interface

    :param string  name: interface name

    :return: returns an interface
    :rtype: interface object
    """

    intfs[name] = ocq.qos.interfaces.interface.add(name)
    intfs[name].config.interface_id = name

    return intfs[name]

def add_sched_policy_to_interface(intf_name, sp_name):
    """Add a scheduler policy name to the interfaces output config

    :param string   intf_name: interface name
    :param string   sp_name : scheduler policy name
    """

    intfs[intf_name].output.scheduler_policy.config.name = sp_name

    return

def setup_interfaces():
    """Setup base interfaces"""

    add_interface("if1")
    add_interface("if2")

    return

def print_qos():
    """Print the QoS object"""

    print "ocq: {}".format(json.dumps(ocq.get(), indent=4))

    return

