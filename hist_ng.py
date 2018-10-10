#!/usr/bin/python3

import os
import sys

import argparse
import json
import sqlite3


HOME_DIR = os.path.expanduser("~")


def db_conn(config):
    if not os.path.isfile(config['database']):
        init_db()

    return sqlite3.connect(config['database'])


def init_db():
    raise Exception("Must initialize database prior to using.")


def save_command(conn, command):
    cur = conn.cursor()

    command_id = None

    try:
        cur.execute("INSERT INTO commands VALUES (?);", [command])
        command_id = cur.lastrowid
    except sqlite3.IntegrityError:
        cur.execute("SELECT ROWID FROM commands WHERE value=? LIMIT 1;", [command])
        row = cur.fetchone()
        command_id = row[0]

    conn.commit()
    cur.close()

    return command_id


def save_project(conn, project):
    cur = conn.cursor()

    project_id = None

    try:
        cur.execute("INSERT INTO projects VALUES (?);", [project])
        project_id = cur.lastrowid
    except sqlite3.IntegrityError:
        cur.execute("SELECT ROWID FROM projects WHERE name=? LIMIT 1;", [project])
        row = cur.fetchone()
        project_id = row[0]

    conn.commit()
    cur.close()

    return project_id


def save_session(conn, session):
    cur = conn.cursor()

    session_id = None

    try:
        cur.execute("INSERT INTO sessions VALUES (?);", [session])
        session_id = cur.lastrowid
    except sqlite3.IntegrityError:
        cur.execute("SELECT ROWID FROM sessions WHERE name=? LIMIT 1;", [session])
        row = cur.fetchone()
        session_id = row[0]

    conn.commit()
    cur.close()

    return session_id


def save_context(conn, command_id, project_id, session_id):
    cur = conn.cursor()

    pwd = os.getcwd()
    row = [command_id, project_id, session_id, pwd]

    cur.execute("INSERT INTO executions (command_id, project_id, " +
                "session_id, pwd) VALUES (?, ?, ?, ?);", row)

    conn.commit()
    cur.close()


def save(config, command, project, session):
    conn = db_conn(config)

    command_id = save_command(conn, command)
    project_id = save_project(conn, project)
    session_id = save_session(conn, session)

    save_context(conn, command_id, project_id, session_id)

    conn.commit()
    conn.close()


def get_session_history(conn, session_id):
    cur = conn.cursor()

    cur.execute("SELECT command_id FROM executions WHERE session_id=? ORDER BY exec_time ASC;", [session_id])
    rows = cur.fetchall()

    results = []
    for row in rows:
        command_id = row[0]
        cur.execute("SELECT value FROM commands WHERE ROWID=? LIMIT 1;", [command_id])
        row = cur.fetchone()
        command = row[0]
        results.append(command)

    cur.close()
    return results


def write_history(history, path):
    history_file = open(path, 'w')
    for line in history:
        history_file.write("%s\n" % line)
    history_file.flush()
    history_file.close()


def write_session(config, session):
    conn = db_conn(config)

    session_id = save_session(conn, session)
    session_file = "%d.hist-ng" % session_id
    session_path = os.path.join(config['sessions_dir'], session_file)

    session_history = get_session_history(conn, session_id)
    write_history(session_history, session_path)

    print(session_path)

    conn.commit()
    conn.close()


def write_project(config, project):
    conn = db_conn(config)

    project_id = save_project(conn, project)

    conn.commit()
    conn.close()

def parse_args():
    desc = "Project-centric bash shell history management"
    parser = argparse.ArgumentParser(prog="hist-ng", description=desc)

    hist_config = os.path.join(HOME_DIR, ".hist_ng", "config.json")
    config_value = os.environ.get('HIST_NG_CONFIG', hist_config)

    session_value = os.environ.get('HIST_NG_SESSION', None)
    session_required = True
    session_nargs = None
    if session_value:
        session_required = None
        session_nargs="?"

    project_value = os.environ.get('HIST_NG_PROJECT', None)
    project_required = True
    project_nargs = None
    if project_value:
        project_required = None
        project_nargs="?"

    parser.add_argument('-c', '--config', type=argparse.FileType('r'),
                        default=config_value,
                        help="Location of hist_ng configuration file.")

    subparsers = parser.add_subparsers()

    cmd_action = subparsers.add_parser('cmd')
    cmd_action.add_argument('-s', '--session', type=str,
                            default=session_value, required=session_required,
                            help="Session the command was executed in; " +
                            "defaults to the value of HIST_NG_SESSION")
    cmd_action.add_argument('-p', '--project', type=str,
                            default=project_value, required=project_required,
                            help="Context or project to save the command in; " +
                            "defaults to the value of HIST_NG_PROJECT")
    cmd_action.add_argument('command', help="Command to save")
    cmd_action.set_defaults(which='save')

    session_action = subparsers.add_parser('session')
    session_action.add_argument('session',
                                default=session_value, nargs=session_nargs,
                                help="Session to write history for")
    session_action.set_defaults(which='write_session')

    project_action = subparsers.add_parser('project')
    project_action.add_argument('project',
                                default=project_value, nargs=project_nargs,
                                help="Project to write history for")
    project_action.add_argument('path', help="Location to write history")
    project_action.set_defaults(which='write_project')

    args = parser.parse_args()
    if 'which' not in args:
        parser.print_help()
        sys.exit(1)

    return args


def parse_config(config_fp):
    config = json.load(config_fp)

    # Validate "database" config value
    if "database" not in config:
        raise ValueError("Missing global key database in configuration: " +
                         config_path)
    if not isinstance(config['database'], str):
        raise ValueError("Global key database not of type str in " +
                         "configuration: " + config_path)

    # Validate "sessions_dir" config value
    if "sessions_dir" not in config:
        raise ValueError("Missing global key sessions_dir in configuration: " +
                         config_path)
    if not isinstance(config['sessions_dir'], str):
        raise ValueError("Global key sessions_dir not of type str in " +
                         "configuration: " + config_path)
    os.makedirs(config['sessions_dir'], exist_ok=True)

    # Validate "projects" config value
    if "projects" not in config:
        raise ValueError("Missing global key projects in configuration: " +
                         config_path)
    if "default" not in config['projects']:
        raise ValueError("Missing subkey default of global key projects " +
                         "in configuration: " + config_path)

    config['database'] = os.path.expanduser(config['database'])
    config['sessions_dir'] = os.path.expanduser(config['sessions_dir'])

    return config


def main():
    args = parse_args()
    config = parse_config(args.config)

    if args.which == 'save':
        save(config, args.command, args.project, args.session)
    elif args.which == 'write_session':
        write_session(config, args.session)
    elif args.which == 'write_project':
        write_project(config, args.project)


if __name__ == "__main__":
    main()
