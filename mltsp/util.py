import subprocess
from subprocess import Popen, PIPE
import os
import numpy as np

try:
    import docker
    dockerpy_installed = True
except ImportError:
    dockerpy_installed = False
import requests


def get_docker_client(version='1.14'):
    """Connect to Docker if available and return a client.

    Parameters
    ----------
    version : str, optional
        Protocol version.

    Returns
    -------
    docker.Client
        Docker client.

    Raises
    ------
    RuntimeError
        If Docker cannot be contacted or contains no images.
    """
    docker_socks = ['/var/run/docker.sock', '/docker.sock']

    if not dockerpy_installed:
        raise RuntimeError('docker-py required for docker operations')

    # First try to auto detect docker parameters from environment
    try:
        args = docker.utils.kwargs_from_env(assert_hostname=False)
        args.update(dict(version=version))
        cli = docker.Client(**args)
        cli.info()
        return cli
    except requests.exceptions.ConnectionError:
        pass

    for sock in docker_socks:
        if os.path.exists(sock):
            try:
                cli = docker.Client(base_url='unix://{}'.format(sock), version=version)
                cli.info()
                return cli
            except requests.exceptions.ConnectionError:
                pass

    raise RuntimeError('Could not locate a usable docker socket')


def docker_images_available():
    """Return boolean indicating whether Docker images are present."""
    if not dockerpy_installed:
        return False

    try:
        cli = get_docker_client()
        img_ids = cli.images(quiet=True)
    except RuntimeError:
        return False

    return len(img_ids) > 0


def is_running_in_docker():
    """Return bool indicating whether running in a Docker container."""
    import subprocess
    if not os.path.exists("/proc/1/cgroup"):
        return False
    proc = subprocess.Popen(["cat", "/proc/1/cgroup"], stdout=subprocess.PIPE)
    output = proc.stdout.read()
    if "/docker/" in str(output):
        in_docker_container = True
    else:
        in_docker_container = False
    return in_docker_container


def cast_model_params(model_type, model_params):
    """Attempt to cast model parameters strings to expected types."""
    from .ext.sklearn_models import model_descriptions
    for entry in model_descriptions:
        if entry["abbr"] == model_type:
            params_list = entry["params"]
            break
    for k, v in model_params.items():
        if v == "None":
            model_params[k] = None
            continue
        for p in params_list:
            if p["name"] == k:
                param_entry = p
                break
        if type(param_entry["type"]) == type or param_entry["type"] == np.array:
            dest_type = param_entry["type"]
            model_params[k] = dest_type(v)
        elif type(param_entry["type"]) == list:
            dest_types_list = param_entry["type"]
            for dest_type in dest_types_list:
                if dest_type != str:
                    try:
                        model_params[k] = dest_type(v)
                        break
                    except:
                        continue
            if type(model_params[k]) == str and str not in dest_types_list:
                raise(ValueError("Model parameter cannot be cast to expected "
                                 "type."))
