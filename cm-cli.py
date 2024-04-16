import os
import sys
import traceback

sys.path.append("./glob")
import manager_core as core
import asyncio

print(f"\n-= ComfyUI-Manager CLI =-\n")

comfyui_manager_path = os.path.dirname(__file__)
comfy_path = os.environ.get('COMFYUI_PATH')

if comfy_path is None:
    print(f"WARN: The `COMFYUI_PATH` environment variable is not set. Assuming `custom_nodes/ComfyUI-Manager/../../` as the ComfyUI path.", file=sys.stderr)
    comfy_path = os.path.abspath(os.path.join(comfyui_manager_path, '..', '..'))

startup_script_path = os.path.join(comfyui_manager_path, "startup-scripts")
custom_nodes_path = os.path.join(comfy_path, 'custom_nodes')

script_path = os.path.join(startup_script_path, "install-scripts.txt")
restore_snapshot_path = os.path.join(startup_script_path, "restore-snapshot.json")


if len(sys.argv) < 3:
    print(f"\npython cm-cli.py [OPTIONS]\n"
          f"OPTIONS:\n"
          f"    [install|uninstall|update|disable|enable] node_name ... ?[--channel <channel name>] ?[--mode [remote|local|cache]]\n"
          f"    [simple-show|show] [installed|enabled|not-installed|disabled|all]\n"
          f"    [save-snapshot|restore-snapshot] <snapshot>\n"
          f"    clear\n")
    exit(-1)


channel = 'default'
mode = 'remote'
nodes = set()


def load_custom_nodes():
    channel_dict = core.get_channel_dict()
    if channel not in channel_dict:
        print(f"ERROR: Invalid channel is specified `--channel {channel}`", file=sys.stderr)
        exit(-1)

    if mode not in ['remote', 'local', 'cache']:
        print(f"ERROR: Invalid mode is specified `--mode {mode}`", file=sys.stderr)
        exit(-1)

    channel_url = channel_dict[channel]

    res = {}
    json_obj = asyncio.run(core.get_data_by_mode(mode, 'custom-node-list.json', channel_url=channel_url))
    for x in json_obj['custom_nodes']:
        for y in x['files']:
            if 'github.com' in y and not (y.endswith('.py') or y.endswith('.js')):
                repo_name = y.split('/')[-1]
                res[repo_name] = x

    return res


def process_args():
    global channel
    global mode

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--channel':
            if i+1 < len(sys.argv):
                channel = sys.argv[i+1]
                i += 1
        elif sys.argv[i] == '--mode':
            if i+1 < len(sys.argv):
                mode = sys.argv[i+1]
                i += 1
        else:
            nodes.add(sys.argv[i])

        i += 1


process_args()
custom_node_map = load_custom_nodes()


def lookup_node_path(node_name):
    # Currently, the node_name is used directly as the node_path, but in the future, I plan to allow nicknames.
    if node_name in custom_node_map:
        return node_name, custom_node_map[node_name]

    print(f"ERROR: invalid node name '{node_name}'")
    exit(-1)


def install_node(node_name):
    node_path, node_item = lookup_node_path(node_name)
    res = core.gitclone_install(node_item['files'], instant_execution=True)
    if not res:
        print(f"ERROR: An error occurred while installing '{node_name}'.")


def uninstall_node(node_name):
    node_path, node_item = lookup_node_path(node_name)
    res = core.gitclone_uninstall(node_item['files'])
    if not res:
        print(f"ERROR: An error occurred while uninstalling '{node_name}'.")


def update_node(node_name):
    node_path, node_item = lookup_node_path(node_name)
    res = core.gitclone_update(node_item['files'], instant_execution=True)
    if not res:
        print(f"ERROR: An error occurred while uninstalling '{node_name}'.")


def enable_node(node_name):
    node_path, _ = lookup_node_path(node_name)

    if os.path.exists(node_path+'.disabled'):
        current_name = node_path+'.disabled'
        new_name = node_path[:-9]
        os.rename(current_name, new_name)
    elif os.path.exists(node_path):
        print(f"WARN: '{node_path}' is enabled already.")
    else:
        print(f"WARN: '{node_path}' is not installed.")


def disable_node(node_name):
    node_path, _ = lookup_node_path(node_name)

    if os.path.exists(node_path):
        current_name = node_path
        new_name = node_path+'.disabled'
        os.rename(current_name, new_name)
    elif os.path.exists(node_path+'.disabled'):
        print(f"WARN: '{node_path}' is disabled already.")
    else:
        print(f"WARN: '{node_path}' is not installed.")


def show_list(kind, simple=False):
    for k, v in custom_node_map.items():
        node_path = os.path.join(custom_nodes_path, k)

        states = set()
        if os.path.exists(node_path):
            prefix = '[    ENABLED    ] '
            states.add('installed')
            states.add('enabled')
            states.add('all')
        elif os.path.exists(node_path+'.disabled'):
            prefix = '[    DISABLED   ] '
            states.add('installed')
            states.add('disabled')
            states.add('all')
        else:
            prefix = '[ NOT INSTALLED ] '
            states.add('not-installed')
            states.add('all')

        if kind in states:
            if simple:
                print(f"{k:50}")
            else:
                print(f"{prefix} {k:50}(author: {v['author']})")


def cancel():
    if os.path.exists(script_path):
        os.remove(script_path)

    if os.path.exists(restore_snapshot_path):
        os.remove(restore_snapshot_path)


def for_each_nodes(act):
    for x in nodes:
        node_path = os.path.join(custom_nodes_path, x)
        try:
            act(node_path)
        except Exception as e:
            print(f"ERROR: {e}")
            traceback.print_exc()


op = sys.argv[1]


if op == 'install':
    for_each_nodes(install_node)

elif op == 'uninstall':
    for_each_nodes(uninstall_node)

elif op == 'update':
    for_each_nodes(update_node)

elif op == 'disable':
    for_each_nodes(disable_node)

elif op == 'enable':
    for_each_nodes(enable_node)

elif op == 'show':
    show_list(sys.argv[2])

elif op == 'simple-show':
    show_list(sys.argv[2], True)

elif op == 'clear':
    cancel()

