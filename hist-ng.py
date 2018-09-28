#!/usr/bin/python3

import os
import sys

import argparse
import sqlite3


HOME_DIR = os.path.expanduser("~")
HIST_DIR = os.path.join(HOME_DIR, ".hist_ng")
HIST_DB = os.path.join(HIST_DIR, "history.db")
HIST_CONF = os.path.join(HIST_DIR, "config.json")


def db_conn():
    if not os.path.isdir(HIST_DIR):
        os.makedirs(HIST_DIR)

    if not os.path.isfile(HIST_DB):
        init_db()

    return sqlite3.connect(HIST_DB)


def init_db():
    raise Exception("Must initialize database prior to using.")


def save_command(conn, command):
    cur = conn.cursor()

    command_id = None

    try:
        r = cur.execute("INSERT INTO commands VALUES (?);", [command])
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
        r = cur.execute("INSERT INTO projects VALUES (?);", [project])
        project_id = cur.lastrowid
    except sqlite3.IntegrityError:
        cur.execute("SELECT ROWID FROM projects WHERE name=? LIMIT 1;", [project])
        row = cur.fetchone()
        project_id = row[0]

    conn.commit()
    cur.close()

    return project_id


def save_context(conn, command_id, project_id):
    cur = conn.cursor()

    pwd = os.getcwd()
    row = [command_id, project_id, pwd]

    cur.execute("INSERT INTO executions (command_id, project_id, pwd) VALUES (?, ?, ?);", row)

    conn.commit()
    cur.close()


def save(command, project):
    conn = db_conn()

    command_id = save_command(conn, command)
    project_id = save_project(conn, project)

    save_context(conn, command_id, project_id)

    conn.commit()
    conn.close()


def parse_args():
    desc = "Project-centric bash shell history management"
    parser = argparse.ArgumentParser(prog="hist-ng", description=desc)

    subparsers = parser.add_subparsers()

    save_action = subparsers.add_parser('save')
    save_action.add_argument('command', help="Command to save")
    save_action.add_argument('project', default="global", nargs='?',
                             help="Context or project to save the command in")
    save_action.set_defaults(which='save')

    return parser.parse_args()


def main():
    args = parse_args()

    if args.which == 'save':
        save(args.command, args.project)

    #save("ls")
    pass


if __name__ == "__main__":
    main()
