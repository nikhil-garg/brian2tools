"""
The file contains simple functions to collect information
from BrianObjects and represent them in a standard
dictionary format. The parts of the file shall be reused
with standard format exporter.
"""
from brian2.equations.equations import PARAMETER
from brian2.utils.stringtools import get_identifiers
from brian2.groups.neurongroup import StateUpdater
from brian2.groups.group import CodeRunner
from brian2.synapses.synapses import SummedVariableUpdater
from .helper import _prune_identifiers


def collect_NeuronGroup(group, run_namespace):
    """
    Collect information from `brian2.groups.neurongroup.NeuronGroup`
    and return them in a dictionary format

    Parameters
    ----------
    group : brian2.groups.neurongroup.NeuronGroup
        NeuronGroup object

    run_namespace : dict
        Namespace dictionary

    Returns
    -------
    neuron_dict : dict
        Dictionary with extracted information
    """
    neuron_dict = {}

    # identifiers belonging to the NeuronGroup
    identifiers = set()

    # get name
    neuron_dict['name'] = group.name

    # get size
    neuron_dict['N'] = group._N

    # get user defined stateupdation method
    if isinstance(group.method_choice, str):
        neuron_dict['user_method'] = group.method_choice
    # if not specified by user
    # TODO collect from run time
    else:
        neuron_dict['user_method'] = None

    # get equations
    neuron_dict['equations'] = collect_Equations(group.user_equations)
    identifiers = identifiers | group.user_equations.identifiers

    # check spike event is defined
    if group.events:
        neuron_dict['events'], event_identifiers = collect_Events(group)
        identifiers = identifiers | event_identifiers

    # resolve group-specific identifiers
    identifiers = group.resolve_all(identifiers, run_namespace)
    # with the identifiers connected to group, prune away unwanted
    identifiers = _prune_identifiers(identifiers)
    # check the dictionary is not empty
    if identifiers:
        neuron_dict['identifiers'] = identifiers

    # check any `run_regularly` / CodeRunner objects associated
    for obj in group.contained_objects:
        # Note: Thresholder, StateUpdater, Resetter are all derived from
        # CodeRunner, so to identify `run_regularly` object we use type()
        if type(obj) == CodeRunner:
            if 'run_regularly' not in neuron_dict:
                neuron_dict['run_regularly'] = []
            neuron_dict['run_regularly'].append({
                                                'name': obj.name,
                                                'code': obj.abstract_code,
                                                'dt': obj.clock.dt,
                                                'when': obj.when,
                                                'order': obj.order
                                                })
        # check StateUpdater when/order and assign to group level
        if isinstance(obj, StateUpdater):
            neuron_dict['when'] = obj.when
            neuron_dict['order'] = obj.order

        # check Threshold

    return neuron_dict


def collect_Equations(equations):
    """
    Collect model equations of the NeuronGroup

    Parameters
    ----------
    equations : brian2.equations.equations.Equations
        model equations object

    Returns
    -------
    eqn_dict : dict
        Dictionary with extracted information
    """

    eqn_dict = {}

    for name in (equations.diff_eq_names | equations.subexpr_names |
                 equations.parameter_names):

        eqs = equations[name]

        eqn_dict[name] = {'unit': eqs.unit,
                          'type': eqs.type,
                          'var_type': eqs.var_type}

        if eqs.type != PARAMETER:
            eqn_dict[name]['expr'] = eqs.expr.code

        if eqs.flags:
            eqn_dict[name]['flags'] = eqs.flags

    return eqn_dict


def collect_Events(group):

    """
    Collect Events (spiking) of the NeuronGroup

    Parameters
    ----------
    group : brian2.groups.neurongroup.NeuronGroup
        NeuronGroup object

    Returns
    -------
    event_dict : dict
        Dictionary with extracted information

    event_identifiers : set
        Set of identifiers related to events
    """

    event_dict = {}
    event_identifiers = set()

    # loop over the thresholder to check `spike` or custom event
    for event in group.thresholder:
        # for simplicity create subdict variable for particular event
        event_dict[event] = {}
        event_subdict = event_dict[event]
        # add threshold
        event_subdict['threshold'] = {'code': group.events[event],
                                      'when': group.thresholder[event].when,
                                      'order': group.thresholder[event].order,
                                      'dt': group.thresholder[event].clock.dt}
        event_identifiers |= (get_identifiers(group.events[event]))

        # check reset is defined
        if event in group.event_codes:
            event_subdict['reset'] = {'code': group.event_codes[event],
                                      'when': group.resetter[event].when,
                                      'order': group.resetter[event].order,
                                      'dt': group.resetter[event].clock.dt}
            event_identifiers |= (get_identifiers(group.event_codes[event]))

    # check refractory is defined (only for spike event)
    if event == 'spike' and group._refractory:
        event_subdict['refractory'] = group._refractory

    return event_dict, event_identifiers


def collect_SpikeGenerator(spike_gen, run_namespace=None):
    """
    Extract information from
    'brian2.input.spikegeneratorgroup.SpikeGeneratorGroup'and
    represent them in a dictionary format

    Parameters
    ----------
    spike_gen : brian2.input.spikegeneratorgroup.SpikeGeneratorGroup
            SpikeGenerator object

    run_namespace : dict
            Namespace dictionary

    Returns
    -------
    spikegen_dict : dict
                Dictionary with extracted information
    """

    spikegen_dict = {}

    # get name
    spikegen_dict['name'] = spike_gen.name

    # get size
    spikegen_dict['N'] = spike_gen.N

    # get indices of spiking neurons
    spikegen_dict['indices'] = spike_gen._neuron_index[:]

    # get spike times for defined neurons
    spikegen_dict['times'] = spike_gen.spike_time[:]

    # get spike period (default period is 0*second will be stored if not
    # mentioned by the user)
    spikegen_dict['period'] = spike_gen.period[:]

    # `run_regularly` / CodeRunner objects of spike_gen
    # although not a very popular option
    for obj in spike_gen.contained_objects:
        if type(obj) == CodeRunner:
            if 'run_regularly' not in spikegen_dict:
                spikegen_dict['run_regularly'] = []
            spikegen_dict['run_regularly'].append({
                                                'name': obj.name,
                                                'code': obj.abstract_code,
                                                'dt': obj.clock.dt,
                                                'when': obj.when,
                                                'order': obj.order
                                                })

    return spikegen_dict


def collect_PoissonGroup(poisson_grp, run_namespace):
    """
    Extract information from 'brian2.input.poissongroup.PoissonGroup'
    and represent them in a dictionary format

    Parameters
    ----------
    poisson_grp : brian2.input.poissongroup.PoissonGroup
            PoissonGroup object

    run_namespace : dict
            Namespace dictionary

    Returns
    -------
    poisson_grp_dict : dict
                Dictionary with extracted information
    """

    poisson_grp_dict = {}
    poisson_identifiers = set()

    # get name
    poisson_grp_dict['name'] = poisson_grp._name

    # get size
    poisson_grp_dict['N'] = poisson_grp._N

    # get rates (can be Quantity or str)
    poisson_grp_dict['rates'] = poisson_grp._rates
    if type(poisson_grp._rates) == str:
        poisson_identifiers |= (get_identifiers(poisson_grp._rates))

    # resolve object-specific identifiers
    poisson_identifiers = poisson_grp.resolve_all(poisson_identifiers,
                                                  run_namespace)
    # prune away unwanted from the identifiers connected to poissongroup
    poisson_identifiers = _prune_identifiers(poisson_identifiers)
    # check identifiers are present
    if poisson_identifiers:
        poisson_grp_dict['identifiers'] = poisson_identifiers

    # `run_regularly` / CodeRunner objects of poisson_grp
    for obj in poisson_grp.contained_objects:
        if type(obj) == CodeRunner:
            if 'run_regularly' not in poisson_grp_dict:
                poisson_grp_dict['run_regularly'] = []
            poisson_grp_dict['run_regularly'].append({
                                                'name': obj.name,
                                                'code': obj.abstract_code,
                                                'dt': obj.clock.dt,
                                                'when': obj.when,
                                                'order': obj.order
                                                })

    return poisson_grp_dict


def collect_StateMonitor(state_mon):
    """
    Collect details of `brian2.monitors.statemonitor.StateMonitor`
    and return them in dictionary format

    Parameters
    ----------
    state_mon : brian2.monitors.statemonitor.StateMonitor
            StateMonitor object

    Returns
    -------
    state_mon_dict : dict
            Dictionary representation of the collected details
    """

    state_mon_dict = {}

    # get name
    state_mon_dict['name'] = state_mon.name

    # get source object name
    state_mon_dict['source'] = state_mon.source.name

    # get recorded variables
    state_mon_dict['variables'] = state_mon.record_variables

    # get record indices
    # if all members of the source object are being recorded
    # set 'record_indices' = True, else save indices
    if state_mon.record_all:
        state_mon_dict['record'] = state_mon.record_all
    else:
        state_mon_dict['record'] = state_mon.record

    # get no. of record indices
    state_mon_dict['n_indices'] = state_mon.n_indices

    # get clock dt of the StateMonitor
    state_mon_dict['dt'] = state_mon.clock.dt

    # get when and order of the StateMonitor
    state_mon_dict['when'] = state_mon.when
    state_mon_dict['order'] = state_mon.order

    return state_mon_dict


def collect_SpikeMonitor(spike_mon):
    """
    Collect details of `brian2.monitors.spikemonitor.SpikeMonitor`
    and return them in dictionary format

    Parameters
    ----------
    spike_mon : brian2.monitors.spikemonitor.SpikeMonitor
            SpikeMonitor object

    Returns
    -------
    spike_mon_dict : dict
            Dictionary representation of the collected details
    """
    # pass to EventMonitor as they both are identical
    spike_mon_dict = collect_EventMonitor(spike_mon)
    return spike_mon_dict


def collect_EventMonitor(event_mon):
    """
    Collect details of `EventMonitor` class
    and return them in dictionary format

    Parameters
    ----------
    event_mon : brian2.EventMonitor
            EventMonitor object

    Returns
    -------
    event_mon_dict : dict
            Dictionary representation of the collected details
    """

    event_mon_dict = {}

    # collect name
    event_mon_dict['name'] = event_mon.name

    # collect event name
    event_mon_dict['event'] = event_mon.event

    # collect source object name
    event_mon_dict['source'] = event_mon.source.name

    # collect record variables, (done same as for SpikeMonitor)
    event_mon_dict['variables'] = list(event_mon.record_variables)

    # collect record indices and time
    event_mon_dict['record'] = event_mon.record

    # collect time-step
    event_mon_dict['dt'] = event_mon.clock.dt

    # collect when and order
    event_mon_dict['when'] = event_mon.when
    event_mon_dict['order'] = event_mon.order

    return event_mon_dict


def collect_PopulationRateMonitor(poprate_mon):
    """
    Represent required details of PopulationRateMonitor
    in dictionary format

    Parameters
    ----------
    poprate_mon : brian2.monitors.ratemonitor.PopulationRateMonitor
            PopulationRateMonitor class object

    Returns
    -------
    poprate_mon_dict : dict
            Dictionary format of the details collected
    """

    poprate_mon_dict = {}

    # collect name
    poprate_mon_dict['name'] = poprate_mon.name

    # collect source object
    poprate_mon_dict['source'] = poprate_mon.source.name

    # collect time-step
    poprate_mon_dict['dt'] = poprate_mon.clock.dt

    # collect when/order
    poprate_mon_dict['when'] = poprate_mon.when
    poprate_mon_dict['order'] = poprate_mon.order

    return poprate_mon_dict


def collect_Synapses(synapses, run_namespace = None):
    """
    Collect information from `brian2.synapses.synapses.Synapses`
    and represent them in dictionary format

    Parameters
    ----------
    synapses : brian2.synapses.synapses.Synapses
        Synapses object

    run_namespace : dict
        Namespace dictionary

    Returns
    -------
    synapse_dict : dict
        Standard dictionary format with collected information
    """

    synapse_dict = {}
    # get synapses object name
    synapse_dict['name'] = synapses.name

    # get source and target groups
    synapse_dict['source'] = synapses.source.name
    synapse_dict['target'] = synapses.target.name

    # get governing equations
    synapse_dict['equations'] = collect_Equations(synapses.equations)
    if synapses.event_driven:
        synapse_dict['equations'].update(collect_Equations(synapses.event_driven))

    # loop over the contained objects
    summed_variables = []
    for obj in synapses.contained_objects:
        # check summed variables
        if isinstance(obj, SummedVariableUpdater):
            summed_var = {'code': obj.abstract_code, 'target': obj.target.name,
                          'name': obj.name, 'dt': obj.clock.dt,
                          'when': obj.when, 'order': obj.order
                         }
            summed_variables.append(summed_var)

    # check any summed variables are used
    if summed_variables:
        synapse_dict['summed_variables'] = summed_variables

    return synapse_dict
