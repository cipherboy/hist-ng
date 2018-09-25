# hist-ng

Project-centric bash shell history management.


## Problem Overview

The `hist-ng` project aims to solve the problem of context management around
shell history. Notably lacking from most default shell installations--and
many custom dotfile hacks--is a concept of project and project hierarchy.

Consider a developer with the following project setup:

    /personal/project_a
    /personal/project_b
    /org_a/project_c
    /org_a/project_d

If a single global history is used, as per the default on every operating
system install known to the author, all five project's histories are mixed
and muddied. If a per-directory (or per git-repository or similar structure)
history file is set, then there is no way to establish the connection
between project c and d, if one exists. (Say, front- and back-end code to
the same underlying project).

Further, if these projects have their specific histories "seeded" from the
global history, it might be desirable to sync history back into the global
history, so commands run against one project can be more easily found
in the global context.


## Problem Statement

`hist-ng` wishes to solve the following use-cases for history management:

 - Maintaining per-project history and context.
 - Creating filters comining multiple project histories.
 - Merging per-project history into the global context.
 - Searching all history from any context.

By "history and context", we currently mean the following four pieces of
information:

 - The literal text of the last run command.
 - The project the command was run in.
 - The directory the command was run in.
 - The time at which the command was run.

By "filters combing multiple project histories", we currently mean the
following:

 - Interleave by time executed, or concatenate, multiple project histories.
 - Ignore desired commands, by regex or substring matching.

By merging per-project histories into the global context, we mean the
same as above, but only by interleaving commands across all tracked
projects. Projects that are explicitly excluded will be ignored.

By searching, we wish to filter searches quickly and efficiently with an
output format similar to the standard `history` tool.

Initially this should focus on correctness before speed and optimize later
if necessary. At this time, no import tool is planned, but would be useful
in the future. Lastly, auto-project detection should be implemented, allowing
commands containing paths or programs to be always tagged to a specific
project.


## Development Overview

This project contains several useful parts:

 - `bash_helper.sh` -- a collection of bash functions for using `hist-ng` in
   a bash shell. This contains functions for getting and saving the last
   command and triggering it on each prompt.

 - `hist-ng.py` -- a Python 3 script for managing project history. This is
   what does the heavy lifting and maintains the SQLite database and raw
   `bash_history` files.

 - `database.sql` -- a database creation script for use during initial setup
   phase. At some point it might be replaced by a purely Python installer.

 - `config.json` -- a sample configuration script for use with `hist-ng`.
   This shows all of the possible options and serves as documentation of the
   configuration format. Note that it is a `JSON` document and must lint as
   such. (`python3 -m json.tool /path/to/config.json`)

 - `LICENSE` -- `hist-ng` is licensed under the GPLv3 license.


## Usage

Please make sure you have Python3 and the `sqlite3` module. Then:

 1. Copy the `hist-ng.py` to a suitable location.
 2. Add the contents of `bash_helper.sh` into your `bashrc` files.
 3. Update the location of `HIST_NG_PATH` to point at the location from (1).
 4. Run `hist-ng <init>`. This initializes `hist-ng` and creates a config
    directory, `$HOME/.hist-ng` if it doesn't exist. You can then modify the
    configuration in `$HOME/.hist-ng/config.json` as desired.

That's it! Have fun using `hist-ng`.


## Miscellaneous

To report issues, please see the Issues tab on GitHub.
