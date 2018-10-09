CREATE TABLE commands (
    -- rowid
    value TEXT UNIQUE
);

CREATE TABLE projects (
    -- rowid
    name TEXT UNIQUE
);

CREATE TABLE sessions (
    -- rowid
    name TEXT UNIQUE
);

CREATE TABLE executions (
    command_id INTEGER,
    project_id INTEGER,
    session_id INTEGER,

    pwd TEXT,
    exec_time DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(command_id) REFERENCES commands(ROWID),
    FOREIGN KEY(project_id) REFERENCES projects(ROWID)
    FOREIGN KEY(session_id) REFERENCES sessions(ROWID)
);
