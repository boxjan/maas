.. -*- mode: rst -*-

************
Hacking MAAS
************


Coding style
============

MAAS uses linters for Python, Go and Bash code.

Run ``make lint`` to check for issues/errors and ``make format`` to
automatically reformat code.


Prerequisites
=============

Dependencies
^^^^^^^^^^^^

You can grab MAAS's code manually from Launchpad but Git_ makes it
easy to fetch the last version of the code. First of all, install
Git::

    $ sudo apt install git

.. _Git: https://git-scm.com/

Then go into the directory where you want the code to reside and run::

    $ git clone https://git.launchpad.net/maas && cd maas

MAAS depends on Postgres, isc-dhcp, bind9, and many other packages. To install
everything that's needed for running and developing MAAS, run::

    $ make install-dependencies

Careful: this will ``apt install`` many packages on your system, via
``sudo``. It may prompt you for your password.

This will install ``bind9``. As a result you will have an extra daemon
running. If you are a developer and don't intend to run BIND locally, you can
disable the daemon via ``sudo systemctl disable --now named``.

Python development dependencies are pulled automatically from `PyPI`_ in a
virtualenv located under ``.ve``.

.. _PyPI:
  https://pypi.org/


Git Workflow
^^^^^^^^^^^^

You will want to adjust your git repository of lp:maas some before you start
making changes to the code. This includes setting up your own copy of
the repository and making your changes in branches.

First you will want to rename the origin remote to upstream and create a new
origin in your namespace.

::

    $ git remote rename origin upstream
    $ git remote add origin git+ssh://{launchpad-id}@git.launchpad.net/~{launchpad-id}/maas

Now you can make a branch and start making changes.

::

    $ git checkout -b new-branch

Once you have made the changes you want, you should commit and push the branch
to your origin.

::

    $ git commit -m "My change" -a
    $ git push origin new-branch

Now you can view that branch on Launchpad and propose it to the maas
repository.

Once the branch has been merged and your done with it you can update your
git repository to remove the branch.

::

    $ git fetch upstream
    $ git checkout master
    $ git merge upstream/master
    $ git branch -d new-branch


Running tests
=============

To run the whole suite::

    $ make test

To run tests at a lower level of granularity::

    $ ./bin/test.region src/maasserver/tests/test_api.py
    $ ./bin/test.region src/maasserver/tests/test_api.py:AnonymousEnlistmentAPITest

The test runner is `nose`_, so you can pass in options like ``--nocapture``
(short option: ``-s``). This option is essential when using ``pdb`` so that
stdout is not adulterated.

.. _nose: http://readthedocs.org/docs/nose/en/latest/

.. Note::

   When running ``make test`` through ssh from a machine with locales
   that are not set up on the machine that runs the tests, some tests
   will fail with a ``MismatchError`` and an "unsupported locale
   setting" message. Running ``locale-gen`` for the missing locales or
   changing your locales on your workstation to ones present on the
   server will solve the issue.


Emitting subunit
^^^^^^^^^^^^^^^^

Pass the ``--with-subunit`` flag to any of the test runners (e.g.
``bin/test.rack``) to produce a `subunit`_ stream of test results. This
may be useful for parallelising test runs, or to allow later analysis of
a test run. The optional ``--subunit-fd`` flag can be used to direct the
results to a different file descriptor, to ensure a clean stream.

.. _subunit: https://launchpad.net/subunit/


Production MAAS server debugging
================================

When MAAS is installed from packaging it can help to enable debugging features
to triage issues.

Log all API and UI exceptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default MAAS only logs HTTP 500 - INTERNAL_SERVER_ERROR into the
regiond.log. To enable logging of all exceptions even exceptions where MAAS
will return the correct HTTP status code.::

  $ sudo sed -i 's/DEBUG = False/DEBUG = True/g' \
  >   /usr/lib/python3/dist-packages/maasserver/djangosettings/settings.py
  $ sudo service maas-regiond restart

Run regiond in foreground
^^^^^^^^^^^^^^^^^^^^^^^^^

It can help when debugging to run regiond a foreground process so you can
interact with the regiond by placing a breakpoint in the code. Once you have
placed a breakpoint into the code you want to inspect you can start the regiond
process in the foreground.::

  $ sudo service maas-regiond stop
  $ sudo -u maas -H \
  >   DJANGO_SETTINGS_MODULE=maasserver.djangosettings.settings \
  >   twistd3 --nodaemon --pidfile= maas-regiond


.. Note::

   By default a MAAS installation runs 4 regiond processes at the same time.
   This will change it to only run 1 process in the foreground. This should
   only be used for debugging. Once finished the breakpoint should be removed
   and maas-regiond service should be started.

Run rackd in foreground
^^^^^^^^^^^^^^^^^^^^^^^^^

It can help when debugging to run rackd a foreground process so you can
interact with the rackd by placing a breakpoint in the code. Once you have
placed a breakpoint into the code you want to inspect you can start the rackd
process in the foreground.::

   $ sudo service maas-rackd stop
   $ sudo -u maas -H /usr/bin/authbind --deep /usr/bin/twistd3 --nodaemon --pidfile= maas-rackd


Development MAAS server setup
=============================

Access to the database is configured in
``src/maasserver/djangosettings/development.py``.

The test suite sets up a development database cluster inside your branch. It
lives in the ``db`` directory, which gets created on demand. You'll want to
shut it down before deleting a branch; see below.

First, set up the project. This fetches all the required dependencies
and sets up some useful commands in ``bin/``::

    $ make


Development using the snap
==========================

If you want to interact with real machines or VMs, it's better to use the
snap. Instead of building a real snap, though, you can run

::

    $ make snap-tree

to create an unpacked snap in the ``dev-snap/tree`` directory. That has all the
contents of the snap, but it's in a plain directory insted of in a squashfs
image. Using a directory is better for testing, since you can change the files
in there and not rebuild the snap.

You can now install the snap:

::

    $ sudo snap try dev-snap/tree
    $ utilities/connect-snap-interfaces

Note that ``snap try`` is used instead of ``snap install``. The maas snap
should now be installed.

The latter command connects all the interfaces needed
for the snap to work. This is performed automatically by snapd when installing
the snap from the store, but is a manual step when installing via ``snap try``.

::

    $ snap list
    Name          Version                 Rev   Tracking  Publisher   Notes
    core          16-2.41                 7713  stable    canonical✓  core
    core18        20191001                1192  stable    canonical✓  base
    maas          2.7.0-8077-g.7e249fbe4  x1    -         -           try
    maas-cli      0.6.5                   13    stable    canonical✓  -
    snapd         2.41                    4605  stable    canonical✓  snapd

Next you need to initialize the snap, just like you would normally do:

::

    $ sudo maas init

And now you're ready to make changes to the code. After you've change
some source files and want to test them out, run the ``sync-dev-snap``
target again:

::

    $ make snap-tree-sync

You should now see that you files were synced to the prime directory. Restart
the supervisor service to use the synced code:

::

    $ sudo service snap.maas.supervisor restart

VMs or even real machines can now PXE boot off your development snap.
But of course, you need to set up the networking first. If you want to
do some simple testing, the easiest is to create a networking in
virt-manager that has NAT, but doesn't provide DHCP. If the name of
the bridge that got created is `virbr1`, you can expose it to your
container as eth1 using the following config:

::

    eth1:
      name: eth1
      nictype: bridged
      parent: virbr1
      type: nic

Of course, you also need to configure that eth1 interface. Since MAAS is
the one providing DHCP, you need to give it a static address on the
network you created. For example::

    auto eth1
    iface eth1 inet static
      address 192.168.100.2
      netmask 255.255.255.0

Note that your LXD host will have the .1 address and will act as a
gateway for your VMs.


Creating sample data
^^^^^^^^^^^^^^^^^^^^

To create a local Postgres dabase tree (in the ``db/`` directory), run::

    $ make syncdb

In addition, it's possible to generate sample data in the database with::

    $ make sampledata

with an optional (``SAMPLEDATA_MACHINES=<n>`` parameter to specify how many
machines to generate).

The created database can be dumped via::

    $ make dumpdb

(optionally specifying ``DB_DUMP=filename.dump`` for the target file).

The resulting dump can then be imported into a different PostgreSQL server for
MAAS to use.

With maas-test-db, this can be done with the following::

   $ sudo cp maasdb.dump /var/snap/maas-test-db/common
   $ sudo snap run --shell maas-test-db.psql \
     -c 'db-dump restore $SNAP_COMMON/maasdb.dump maassampledata'

and then updating the MAAS configuration to use the new db by editing
``/var/snap/maas/current/regiond.conf`` to point to the new database, and
restarting the snap.

If an external postgres is used a command similar to the following one can be
used to restore the database::

   pg_restore \
     --clean \
     --if-exists \
     --no-owner \
     --no-privileges \
     --role maas \
     --disable-triggers \
     -d maassampledata maasdb.dump

You can review generated data::

    $ sudo maas-test-db.psql

If you don't like an interactive ``psql`` prompt, you can connect via socket
using other tools like `pgcli`_::

    $ sudo pgcli -h /var/snap/maas-test-db/common/postgres/sockets -U postgres

.. _pgcli: https://www.pgcli.com/install


Configuring DHCP
^^^^^^^^^^^^^^^^

MAAS requires a properly configured DHCP server so it can boot machines using
PXE. MAAS can work with its own instance of the ISC DHCP server, if you
install the maas-dhcp package::

    $ sudo apt install maas-dhcp

Note that maas-dhcpd service definition referencese the maas-rackd
service, which won't be present if you run a development service. To
workaround edit /lib/systemd/system/maas-dhcp.service and comment out
this line:

    BindsTo=maas-rackd.service


Non-interactive configuration of RBAC service authentication
============================================================

For development and automating testing purposes, it's possible to configure
maas with the RBAC service in a non-interactive way, with the following::

    $ sudo MAAS_CANDID_CREDENTIALS=user1:password1 maas configauth --rbac-url http://<url-of-rbac>:5000 --rbac-sevice-name <maas-service-name-in-RBAC>

This will automatically handle logging in with Candid, without requiring the
user to fill in the authentication form via browser.


Database information
====================

MAAS uses Django_ to manage changes to the database schema.

.. _Django: https://www.djangoproject.com/

Be sure to have a look at `Django's migration documentation`_ before you make
any change.

.. _Django's migration documentation:
    https://docs.djangoproject.com/en/1.8/topics/migrations/


Changing the schema
^^^^^^^^^^^^^^^^^^^

Once you've made a model change (i.e. a change to a file in
``src/<application>/models/*.py``) you have to run Django's `makemigrations`_
command to create a migration file that will be stored in
``src/<application>/migrations/builtin/``.

Note that if you want to add a new model class you'll need to import it
in ``src/<application>/models/__init__.py``

.. _makemigrations: https://docs.djangoproject.com/en/1.8/ref/django-admin/#django-admin-makemigrations

Generate the migration script with::

    $ ./bin/maas-region makemigrations --name description_of_the_change maasserver

This will generate a migration module named
``src/maasserver/migrations/builtin/<auto_number>_description_of_the_change.py``.
Don't forget to add that file to the project with::

    $ git add src/maasserver/migrations/builtin/<auto_number>_description_of_the_change.py

To apply that migration, run::

    $ make syncdb

If you're developing using the snap, you can run::

    $ sudo snap run --shell maas.supervisor -c "maas-region dbupgrade"

to run pending migrations.


Performing data migration
^^^^^^^^^^^^^^^^^^^^^^^^^

If you need to perform data migration, very much in the same way, you will need
to run Django's `makemigrations`_ command. For instance, if you want to perform
changes to the ``maasserver`` application, run::

    $ ./bin/maas-region makemigrations --empty --name description_of_the_change maasserver

This will generate a migration module named
``src/maasserver/migrations/builtin/<auto_number>_description_of_the_change.py``.
You will need to edit that file and fill the ``operations`` list with the
options that need to be performed. Again, don't forget to add that file to the
project::

    $ git add src/maasserver/migrations/builtin/<auto_number>_description_of_the_change.py

Once the operations have been added, apply that migration with::

    $ make syncdb


Examining the database manually
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you need to get an interactive ``psql`` prompt, you can use `dbshell`_::

    $ bin/maas-region dbshell

.. _dbshell: https://docs.djangoproject.com/en/dev/ref/django-admin/#dbshell

You can use the ``\dt`` command to list the tables in the MAAS database. You
can also execute arbitrary SQL. For example:::

    maasdb=# select system_id, hostname from maasserver_node;
                     system_id                 |      hostname
    -------------------------------------------+--------------------
     node-709703ec-c304-11e4-804c-00163e32e5b5 | gross-debt.local
     node-7069401a-c304-11e4-a64e-00163e32e5b5 | round-attack.local
    (2 rows)


Viewing SQL queries during tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you need to view the SQL queries that are performed during a test, the
`LogSQL` fixture can be used to output all the queries during the test.::

    from maasserver.testing.fixtures import LogSQL
    self.useFixture(LogSQL())

Sometimes you need to see where in the code that query was performed.::

    from maasserver.testing.fixtures import LogSQL
    self.useFixture(LogSQL(include_stacktrace=True))
