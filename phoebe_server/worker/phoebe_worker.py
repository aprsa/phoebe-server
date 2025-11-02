"""PHOEBE worker process."""

import sys
from typing import Any
import zmq
import phoebe
import json
import traceback
import numpy as np
from phoebe import u


def make_json_serializable(obj):
    """Convert numpy arrays to JSON-compatible types."""
    # if isinstance(obj, np.ndarray):
    #     return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, (u.Unit, u.IrreducibleUnit, u.CompositeUnit)):
        return str(obj)
    elif isinstance(obj, u.Quantity):
        return {
            'value': obj.value,
            'unit': make_json_serializable(obj.unit)
        }
    elif isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, np.ndarray)):
        return [make_json_serializable(item) for item in obj]

    return obj


class PhoebeWorker:
    """PHOEBE computation worker."""

    def __init__(self, port: int):
        self.port = port
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.bind(f"tcp://127.0.0.1:{port}")

        # TODO: move to the client and add SDK/API support!
        self.bundle = phoebe.default_binary()
        self.bundle.flip_constraint('mass@primary', solve_for='q@binary')
        self.bundle.flip_constraint('mass@secondary', solve_for='sma@binary')
        self.bundle.add_solver('differential_corrections', solver='dc')
        phoebe.parameters.parameters._contexts.append('ui')

        self.commands = {
            'ping': self.ping,
            'get_parameter': self.get_parameter,
            'get_value': self.get_value,
            'set_value': self.set_value,
            'add_dataset': self.add_dataset,
            'remove_dataset': self.remove_dataset,
            'run_compute': self.run_compute,
            'run_solver': self.run_solver,
            'load_bundle': self.load_bundle,
            'save_bundle': self.save_bundle,
            'get_datasets': self.get_datasets,
            'get_uniqueid': self.get_uniqueid,
            'is_parameter_constrained': self.is_parameter_constrained,
            # auxiliary commands:
            'attach_params': self.attach_params,
        }

        print(f"[phoebe_worker] Running on port {port}")

    def run(self):
        """Main worker loop."""
        while True:
            args = self.socket.recv_json()
            if type(args) is not dict:
                raise ValueError(f'API returned a non-dictionary value: {args}')

            command = args.pop('command')
            if command not in self.commands:
                response = {
                    'success': False,
                    'error': f'API does not recognize command {command}.'
                }
                self.socket.send_json(response)
                continue

            try:
                result = self.commands[command](**args)
                response = {
                    'success': True,
                    'result': make_json_serializable(result)
                }

                self.socket.send_json(response)

            except Exception as e:
                error_response = {
                    'success': False,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
                self.socket.send_json(error_response)

    def ping(self):
        """Health check / readiness probe."""
        return {'status': 'ready'}

    def get_parameter(self, twig):
        par = self.bundle.get_parameter(twig)
        par_dict = par.to_dict()
        par_dict['Class'] = par.__class__.__name__
        return par_dict

    def get_value(self, twig=None, uniqueid=None, **kwargs):
        return self.bundle.get_value(twig=twig, uniqueid=uniqueid)

    def set_value(self, twig=None, uniqueid=None, value=None, **kwargs):
        self.bundle.set_value(twig=twig, uniqueid=uniqueid, value=value)
        return {'success': True}

    def add_dataset(self, **kwargs):
        self.bundle.add_dataset(**kwargs)
        return {}

    def remove_dataset(self, dataset, **kwargs):
        self.bundle.remove_dataset(dataset)
        return {'success': True}

    def run_compute(self, **kwargs):
        self.bundle.run_compute(**kwargs)

        model = {}

        # We now need to traverse all datasets and assign the results accordingly:
        for dataset in self.bundle.datasets:
            kind = self.bundle[f'{dataset}@dataset'].kind  # 'lc' or 'rv'

            model[dataset] = {}
            model[dataset]['times'] = self.bundle.get_value('compute_times', dataset=dataset, context='dataset')
            model[dataset]['phases'] = self.bundle.get_value('compute_phases', dataset=dataset, context='dataset')

            if kind == 'lc':
                model[dataset]['fluxes'] = self.bundle.get_value('fluxes', dataset=dataset, context='model')
            if kind == 'rv':
                model[dataset]['rv1s'] = self.bundle.get_value('rvs', dataset=dataset, component='primary', context='model')
                model[dataset]['rv2s'] = self.bundle.get_value('rvs', dataset=dataset, component='secondary', context='model')

        return {
            'model': model
        }

    def run_solver(self, **kwargs):
        self.bundle.run_solver(**kwargs)
        return {'success': True}

    def load_bundle(self, bundle, **kwargs):
        self.bundle = phoebe.load(json.loads(bundle, object_pairs_hook=phoebe.utils.parse_json))  # type: ignore
        return {'success': True}

    def save_bundle(self, **kwargs):
        return {'bundle': self.bundle.to_json()}

    def get_datasets(self, **kwargs):
        datasets = {}
        for ds in self.bundle.datasets:
            datasets[ds] = {'kind': self.bundle[f'{ds}@dataset'].kind}
        return {'datasets': datasets}

    def get_uniqueid(self, twig, **kwargs):
        return self.bundle.get_parameter(twig).uniqueid

    def is_parameter_constrained(self, twig=None, uniqueid=None, **kwargs):
        par = self.bundle.get_parameter(twig=twig, uniqueid=uniqueid)
        return bool(par.constrained_by)

    def attach_params(self, params: list[dict[str, Any]]):
        """
        Implements adding custom parameters to the bundle. Parameters are
        passed as a list of dictionaries with the following mandatory keys:

        ptype: str
        qualifier: str
        value: Any
        description: str

        Other optional keys depending on the parameter type:

        choices: list[Any] (for 'choice' type)
        context: str

        The backend implements this as:
        ```
        from phoebe.parameters import ChoiceParameter

        parameters = []

        parameters += [ChoiceParameter(
            qualifier='backend',
            value=kwargs.get('backend', 'PHOEBE'),
            choices=['PHOEBE', 'PHOEBAI'],
            description='Backend to use for computations',
            context='ui'
        )]

        self.bundle._attach_params(parameters)
        ```
        """
        from phoebe.parameters import ChoiceParameter, IntParameter, FloatParameter, BoolParameter, StringParameter

        ptype_class = {
            'choice': ChoiceParameter,
            'int': IntParameter,
            'float': FloatParameter,
            'bool': BoolParameter,
            'string': StringParameter,
        }

        parameters = []
        for param in params:
            ptype = param.pop('ptype')
            if ptype not in ptype_class:
                raise ValueError(f"Unsupported parameter type: {ptype}")

            parameters.append(ptype_class[ptype](**param))

        try:
            self.bundle._attach_params(parameters)
        except Exception as e:
            print(f"Error attaching parameters: {e}")

        unique_ids = [par.uniqueid for par in parameters]

        return {'success': True, 'unique_ids': unique_ids}


def main(port: int):
    worker = PhoebeWorker(port)
    worker.run()


if __name__ == "__main__":
    port = int(sys.argv[1])
    main(port)
