#!/usr/bin/python3

"""
hist_ng - command line history management

hist_ng is split into two parts: a command line interface for storing,
searching, and writing history, and a language-specific shell script for
utilizing the command line interface.

This file is the command line interface. We rely on a sqlite3 database for
storing the history. History can be customized through a JSON configuration
file.
"""

import os
import re
import sys
from typing import Generator, Iterable, Optional, Tuple, Union

import argparse
import json
import sqlite3

EXEC_TABLE = "executions"
HOME_DIR = os.path.expanduser("~")

OInt = Optional[int]
ColumnsType = Union[str, Tuple[str]]

def db_conn(config: dict):
    """
    Create a database connection out of the configuration object. If the
    linked database doesn't yet exist, it will be created.
    """
    assert 'database' in config

    # We equate database not existing to database not being initialized.
    # This isn't technically true as an empty database file could exist and
    # we wouldn't create the corresponding tables, but it suffices for now.
    if not os.path.isfile(config['database']):
        init_db()

    return sqlite3.connect(config['database'])


def init_db():
    """
    Initialize a database, creating the required tables.

    At the current time we don't support creating anything, however, we should
    eventually support both creating and migrating an existing database to the
    latest set of columns.
    """
    raise Exception("Must initialize database prior to using.")


def save_command(conn, command: str) -> int:
    """
    Save a command to the database, returning its ROWID. Since commands must
    be unique per the database schema, if the command already exists, we
    query the ROWID from the database.
    """
    cur = conn.cursor()

    # Save is a bit of a misnomer: we try inserting the command and return the
    # ROWID if it succeeds. However,
    command_id = None

    try:
        # Try to insert the command into the database.
        cur.execute("INSERT INTO commands VALUES (?);", [command])
        command_id = cur.lastrowid
    except sqlite3.IntegrityError:
        # We cause an IntegrityError if we insert a command which already
        # exists in the database. So, select it. All other errors are not
        # caught.
        cur.execute("SELECT ROWID FROM commands WHERE value=? LIMIT 1;", [command])
        row = cur.fetchone()
        command_id = row[0]

    # Technically we need to only commit if we write to the database, but
    # we always commit.
    conn.commit()
    cur.close()

    return command_id


def save_project(conn, project: str) -> int:
    """
    Save a project name to the database, returning its ROWID. Since projects
    must be unique per the database schema, if the project already exists, we
    query the ROWID from the database.
    """
    cur = conn.cursor()

    # See comments in save_command(...).
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
    """
    Save a session name to the database, returning its ROWID. Since sessions
    must be unique per the database schema, if the project already exists, we
    query the ROWID from the database.
    """
    cur = conn.cursor()

    # See comments in save_command(...).
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


def save_context(conn, command_id: int, project_id: int, session_id: int) -> None:
    """
    Save the context of a command to the database; we assume that the CWD
    is the same as where the command was executed. This isn't strictly true
    in all cases though: commands which affect the CWD will report the CWD
    after the change, not before. Only by looking backwards in the shell
    history (to the previous command in that session), will the actual CWD
    be revealed then. In most cases this is fine however.

    This could be fixed by saving the PWD on the session object, using it
    to set the PWD for this command, then updating it on the session object
    again.
    """
    cur = conn.cursor()

    # The command's PWD currently isn't yet configurable.
    pwd = os.getcwd()
    row = [command_id, project_id, session_id, pwd]

    cur.execute("INSERT INTO executions (command_id, project_id, " +
                "session_id, pwd) VALUES (?, ?, ?, ?);", row)

    # Unlike the other save_{command,session,project} commands, we don't
    # return a ROWID as these are meant to be read as a list and never
    # updated (and likely never cross-referenced).
    conn.commit()
    cur.close()


def hist_save(config, command: str, project: str, session: str):
    """
    Handle the command line subcommand "save": save a given command to the
    given project and session.
    """
    conn = db_conn(config)

    # Find or get the following objects from the database. The goal of this
    # is to separate the actual commands, projects, or session names from
    # the system it is run on: this should allow us to sync across multiple
    # machines a little better: denormalize the database and sync it to the
    # other system. This also lets us rename sessions and projects by updating
    # one row versus every row.
    #
    # However, it is dependent on sessions being unique across synced systems,
    # so it is recommended that the hostname be included in the session name.
    command_id = save_command(conn, command)
    project_id = save_project(conn, project)
    session_id = save_session(conn, session)

    # Save the execution context of the particular command to the database.
    save_context(conn, command_id, project_id, session_id)

    conn.commit()
    conn.close()


def parse_columns(table: str, cols: Tuple[str]):
    """
    Parse column names into two pieces: absolute column names prefixed with
    the table, and JOIN statements to get values from numerical identifiers.

    This lets us use descriptive names (e.g., "command") and incrementally
    build the required parts of the SELECT statement from it.
    """
    columns = []
    join_clauses = []

    # We require some number of columns to be selected, else we have an issue
    # with the format of our SELECT statement.
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
        elif col == "pwd":
            columns.append(table + ".pwd")
        elif col == "exec_time":
            columns.append(table + ".exec_time")
        else:
            raise ValueError("Unknown column: %s" % col)

    # We can blindly join columns together with a comma
    column = ",".join(columns)

    join = ""
    if join_clauses:
        # If we have one or more JOIN clauses, the syntax is:
        #   <SELECT...> JOIN <condition> [JOIN <condition>....] <WHERE...>
        # So emulate it by joining the conditions with JOIN, and prepending
        # one additional JOIN.
        join = " JOIN " + " JOIN ".join(join_clauses)

    return column, join


def parse_values(table: str, session_id: OInt = None, project_id: OInt = None):
    """
    Parse the parameterized values and WHERE constraint clauses from the
    passed values we're given.
    """
    where_clauses = []
    values = []

    if session_id:
        where_clauses.append(table + ".session_id=?")
        values.append(session_id)
    if project_id:
        where_clauses.append(table + ".project_id=?")
        values.append(project_id)

    where = ""
    if where_clauses:
        # We assume the conjunction here is AND.
        where = " WHERE " + " AND ".join(where_clauses)

    return where, values


def get_history(conn, session_id: OInt = None, project_id: OInt = None,
                cols: ColumnsType = "command") -> Generator:
    """
    Get a history of command executions from the database, filtering by
    session_id and project_id if present, and only showing the specified
    columns. When cols is a single element, the result will be a list of
    elements.
    """
    cur = conn.cursor()

    # We assume cols is a tuple of strings, but allow it to be a lone string
    # in the case of a single column.
    if isinstance(cols, str):
        cols = (cols,)

    column: str = ""
    join: str = ""
    where: str = ""
    values: list = []

    # Parse parameters into a SQL SELECT statement.
    column, join = parse_columns(EXEC_TABLE, cols)
    where, values = parse_values(EXEC_TABLE, session_id, project_id)

    # Build the query
    query = "SELECT " + column + " FROM " + EXEC_TABLE + join + where + " ORDER BY exec_time ASC;"
    query = query.replace("  ", " ")

    # Execute the query, fetching all results.
    cur.execute(query, values)
    rows = cur.fetchall()

    # Generator versus list;
    for row in rows:
        # Contract:
        #   - cols == 1 <=> list of strings;
        #   - cols > 1 <=> list of dictionaries, keys are columns
        if len(cols) == 1:
            yield row[0]
        else:
            result = {}
            for c_id, col in enumerate(cols):
                result[col] = row[c_id]
            yield result

    cur.close()


def write_history(history: Iterable, path: str):
    """
    Write history to the specified path. This assumes that history is a
    Iterbale of strings.
    """
    history_file = open(path, 'w')
    for line in history:
        history_file.write("%s\n" % line)
    history_file.flush()
    history_file.close()


def hist_write(config: dict, session: str, project: str):
    """
    Handle the command line subcommand "write": write the existing history to
    a bash_history file.
    """
    conn = db_conn(config)

    session_id = save_session(conn, session)

    session_file = "%d.hist-ng" % session_id
    session_path = os.path.join(config['sessions_dir'], session_file)
    session_history = get_history(conn, session_id=session_id)
    write_history(session_history, session_path)

    if project in config['projects_map']:
        project_id = save_session(conn, project)
        project_index = config['projects_map'][project]
        project_config = config['projects'][project_index]

        if 'hist_file' in project_config:
            project_path = project_config['hist_file']
            project_history = get_history(conn, project_id=project_id)
            write_history(project_history, project_path)

    conn.commit()
    conn.close()


def format_history(index: int, item: dict, format_str: str, _file=sys.stdout):
    """
    From a format string, write a history item to stdout.
    """
    i: int = 0
    line: str = ""
    while i < len(format_str):
        char = format_str[i]
        next_char = ""
        if i + 1 < len(format_str):
            next_char = format_str[i+1]

        if char == '%':
            if next_char == 'i':
                line += str(index)
            elif next_char == 'c':
                line += item['command']
            elif next_char == 's':
                line += item['session']
            elif next_char == 'p':
                line += item['project']
            elif next_char == 'd':
                line += item['pwd']
            elif next_char == 't':
                line += item['exec_time']
            elif next_char == '%':
                line += "%"
            else:
                line += char + next_char
            i += 2
            continue

        line += char
        i += 1
    print(line)


def hist_list(config, session, project, command, format_str):
    """
    Handle the command line subcommand "list": print out the commands matching
    a pattern, session, and/or project.
    """
    conn = db_conn(config)

    # When specified, filter by session and project name
    session_id = None
    project_id = None
    if session:
        session_id = save_session(conn, session)
    if project:
        project_id = save_project(conn, project)

    # Get all session history: this ends up being a Generator of dictionaries.
    session_history = get_history(conn, session_id=session_id,
                                  project_id=project_id,
                                  cols=["command", "session", "project", "pwd", "exec_time"])

    # When specified, this regex is used to limit the command list.
    cmd_regex = None
    if command:
        cmd_regex = re.compile(command)

    index: int = 0
    for line in session_history:
        if cmd_regex is None or cmd_regex.match(line["command"]):
            format_history(index+1, line, format_str)
            index += 1

    conn.commit()
    conn.close()


def parse_args():
    """
    Parse the command line arguments when invoked from the command line.
    """
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
    write_action.add_argument('-s', '--session', type=str,
                              default=session_value, required=session_required,
                              help="Session to filter history by")
    write_action.add_argument('-p', '--project', type=str,
                              default=project_value, required=project_required,
                              help="Project to filter history by")
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
                                  "values: %%c: command, %%s: session, " + \
                                  "%%p: project, %%d: pwd, %%t: timestamp, " + \
                                  "%%i: command number, %%%% a literal %%",
                             required=False)
    list_action.set_defaults(which='list')

    args = parser.parse_args()
    if 'which' not in args:
        parser.print_help()
        sys.exit(1)

    return args


def parse_config(config_fp):
    """
    From a file pointer to the configuration, parse it and validate the
    structure of the JSON object is as expected.
    """
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
    projects_map = {}
    for p_id, project in enumerate(config['projects']):
        if "name" not in project:
            raise ValueError("Missing name key in project %d in configuration: %s" %
                             (p_id+1, config_path))
        if not isinstance(project["name"], str):
            raise ValueError("In project %d, name not of type str in configuration: %s" %
                             (p_id+1, config_path))
        projects_map[project['name']] = p_id

        if "hist_file" in project:
            if not isinstance(project["hist_file"], str):
                raise ValueError("In project %d,  hist_file not of type str in configuration: %s" %
                                 (p_id+1, config_path))
            project["hist_file"] = os.path.expanduser(project["hist_file"])

    if 'default' not in projects_map:
        raise ValueError("Missing subkey default of global key projects " +
                         "in configuration: " + config_path)

    config['database'] = os.path.expanduser(config['database'])
    config['sessions_dir'] = os.path.expanduser(config['sessions_dir'])
    config['projects_map'] = projects_map
    os.makedirs(config['sessions_dir'], exist_ok=True)

    return config


def main():
    """
    Main method for handling command line arguments.
    """
    args = parse_args()
    config = parse_config(args.config)

    if args.which == 'save':
        hist_save(config, args.command, args.project, args.session)
    elif args.which == 'write':
        hist_write(config, args.session, args.project)
    elif args.which == 'list':
        hist_list(config, args.session, args.project, args.command,
                  args.format)


if __name__ == "__main__":
    main()
