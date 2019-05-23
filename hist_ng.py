#!/usr/bin/python3

import os
import re
import sys
from typing import Optional, Tuple, Union

import argparse
import json
import sqlite3


HOME_DIR = os.path.expanduser("~")

OINT = Optional[int]
COLUMNS_TYPE = Union[str, Tuple[str]]

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


def save_context(conn, command_id: int, project_id: int, session_id: int):
    cur = conn.cursor()

    pwd = os.getcwd()
    row = [command_id, project_id, session_id, pwd]

    cur.execute("INSERT INTO executions (command_id, project_id, " +
                "session_id, pwd) VALUES (?, ?, ?, ?);", row)

    conn.commit()
    cur.close()


def hist_save(config, command: str, project: str, session: str):
    conn = db_conn(config)

    command_id = save_command(conn, command)
    project_id = save_project(conn, project)
    session_id = save_session(conn, session)

    save_context(conn, command_id, project_id, session_id)

    conn.commit()
    conn.close()


def parse_columns(table: str, cols: tuple):
    columns = []
    join_clauses = []

    if not cols:
        raise ValueError("Expected one or more columns")

    for col in cols:
        if col == "command":
            columns.append("commands.value")
            join_clauses.append("commands ON " + table + ".command_id=commands.ROWID")
        elif col == "command_id":
            columns.append(table + ".command_id")
        elif col == "session":
            columns.append("sessions.name")
            join_clauses.append("sessions ON " + table + ".session_id=sessions.ROWID")
        elif col == "session_id":
            columns.append(table + ".session_id")
        elif col == "project":
            columns.append("projects.name")
            join_clauses.append("projects ON " + table + ".project_id=projects.ROWID")
        elif col == "project_id":
            columns.append(table + ".project_id")
        else:
            raise ValueError("Unknown column: %s" % col)

    column = ",".join(columns)
    join = ""
    if join_clauses:
        join = " JOIN " + " JOIN ".join(join_clauses)

    return column, join


def parse_values(table: str, session_id: OINT = None, project_id: OINT = None):
    where_clauses = []
    values = []

    if session_id:
        where_clauses.append(table + "session_id=?")
        values.append(session_id)
    if project_id:
        where_clauses.append(table + "project_id=?")
        values.append(project_id)

    where = ""
    if where_clauses:
        where = " WHERE " + " AND ".join(where_clauses)

    return where, values


def get_history(conn, session_id: OINT = None, project_id: OINT = None, cols: COLUMNS_TYPE = "command"):
    cur = conn.cursor()
    table = "executions"

    if isinstance(cols, str):
        cols = (cols,)

    column: str = ""
    join: str = ""
    where: str = ""
    values: list = []

    column, join = parse_columns(table, cols)
    where, values = parse_values(table, session_id, project_id)

    query = "SELECT " + column + " FROM executions " + join + where + " ORDER BY exec_time ASC;"
    query = query.replace("  ", " ")

    cur.execute(query, values)
    rows = cur.fetchall()

    results = []
    for row in rows:
        if len(cols) == 1:
            results.append(row[0])
        else:
            result = {}
            for c_id, col in enumerate(cols):
                result[col] = row[c_id]
            results.append(result)

    cur.close()
    return results


def write_history(history, path):
    history_file = open(path, 'w')
    for line in history:
        history_file.write("%s\n" % line)
    history_file.flush()
    history_file.close()


def hist_write(config, session, project):
    conn = db_conn(config)

    session_id = save_session(conn, session)
    session_file = "%d.hist-ng" % session_id
    session_path = os.path.join(config['sessions_dir'], session_file)

    session_history = get_history(conn, session_id)
    write_history(session_history, session_path)

    conn.commit()
    conn.close()


def format_history(item, format_str):
    i: int = 0
    line: str = ""
    while i < len(format_str):
        char = format_str[i]
        next_char = ""
        if i + 1 < len(format_str):
            next_char = format_str[i+1]

        if char == '%':
            if next_char == '%':
                line += "%"
            elif next_char == 'c':
                line += item['command']
            elif next_char == 's':
                line += item['session']
            elif next_char == 'p':
                line += item['project']
            else:
                line += char + next_char
            i += 2
            continue

        line += char
        i += 1
    print(line)


def hist_list(config, session, project, command, format_str):
    conn = db_conn(config)

    session_id = None
    project_id = None
    if session:
        session_id = save_session(conn, session)

    session_history = get_history(conn, session_id=session_id,
                                  cols=["command", "session", "project"])

    cmd_regex = None
    if command:
        cmd_regex = re.compile(command)

    for line in session_history:
        if cmd_regex is None or cmd_regex.match(line["command"]):
            format_history(line, format_str)

    conn.commit()
    conn.close()



def parse_args():
    desc = "Project-centric bash shell history management"
    parser = argparse.ArgumentParser(prog="hist-ng", description=desc)

    hist_config = os.path.join(HOME_DIR, ".hist_ng", "config.json")
    config_value = os.environ.get('HIST_NG_CONFIG', hist_config)

    session_value = os.environ.get('HIST_NG_SESSION', None)
    session_required = True
    if session_value:
        session_required = None

    project_value = os.environ.get('HIST_NG_PROJECT', None)
    project_required = True
    if project_value:
        project_required = None

    file_value = os.environ.get('HIST_NG_HISTFILE', None)
    file_required = True
    if file_value:
        file_required = None


    parser.add_argument('-c', '--config', type=argparse.FileType('r'),
                        default=config_value,
                        help="Location of hist_ng configuration file.")

    subparsers = parser.add_subparsers()

    save_action = subparsers.add_parser('save')
    save_action.add_argument('-s', '--session', type=str,
                             default=session_value, required=session_required,
                             help="Session the command was executed in; " +
                             "defaults to the value of HIST_NG_SESSION")
    save_action.add_argument('-p', '--project', type=str,
                             default=project_value, required=project_required,
                             help="Context or project to save the command in; " +
                             "defaults to the value of HIST_NG_PROJECT")
    save_action.add_argument('command', help="Command to save")
    save_action.set_defaults(which='save')

    write_action = subparsers.add_parser('write')
    write_action.add_argument('-s', '--session', default=session_value,
                              help="Session to filter history by")
    write_action.add_argument('-p', '--project', default=project_value,
                              help="Project to filter history by")
    write_action.add_argument('-o', '--histfile',
                              default=file_value, required=file_required,
                              help="Location to write history to")
    write_action.add_argument('-a', '--append', action='store_true',
                              help="Append changes since last write",
                              required=False)
    write_action.set_defaults(which='write')

    list_action = subparsers.add_parser('list')
    list_action.add_argument('-s', '--session', default="",
                             help="Session to filter list by",
                             required=False)
    list_action.add_argument('-p', '--project', default="",
                             help="Project to filter list by",
                             required=False)
    list_action.add_argument('-c', '--command', default="",
                             help="Command (regex) to filter list by (optional)",
                             required=False)
    list_action.add_argument('-f', '--format', default="%c",
                             help="Format to write output with. Possible " + \
                                  "values:\n%%c: command, %%s: session, " + \
                                  "%%p: project, %%%% a literal %%",
                             required=False)
    list_action.set_defaults(which='list')

    args = parser.parse_args()
    if 'which' not in args:
        parser.print_help()
        sys.exit(1)

    return args


def parse_config(config_fp):
    config = json.load(config_fp)
    config_path = config_fp.name

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

    # Validate "projects" config value
    if "projects" not in config:
        raise ValueError("Missing global key projects in configuration: " +
                         config_path)
    have_default = False
    for p_id, project in enumerate(config['projects']):
        if "name" not in project:
            raise ValueError("Missing name key in project %d in configuration: %s" %
                             (p_id+1, config_path))
        if not isinstance(project["name"], str):
            raise ValueError("Project %d name key not of type str in configuration: %s" %
                             (p_id+1, config_path))
        if project["name"] == "default":
            have_default = True

    if not have_default:
        raise ValueError("Missing subkey default of global key projects " +
                         "in configuration: " + config_path)

    config['database'] = os.path.expanduser(config['database'])
    config['sessions_dir'] = os.path.expanduser(config['sessions_dir'])
    os.makedirs(config['sessions_dir'], exist_ok=True)

    return config


def main():
    args = parse_args()
    config = parse_config(args.config)

    if args.which == 'save':
        hist_save(config, args.command, args.project, args.session)
    elif args.which == 'write':
        hist_write(config, args.session, args.project, args.histfile,
                   args.append)
    elif args.which == 'list':
        hist_list(config, args.session, args.project, args.command,
                  args.format)


if __name__ == "__main__":
    main()
