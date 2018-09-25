CREATE TABLE command (
    -- rowid
    value TEXT UNIQUE
);

CREATE TABLE projects (
    -- rowid
    name TEXT UNIQUE
);

CREATE TABLE exec (
    command_id INTEGER,
    project_id INTEGER,

    pwd TEXT,
    exec_time DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(command_id) REFERENCES command(ROWID),
    FOREIGN KEY(project_id) REFERENCES project(ROWID)
);
