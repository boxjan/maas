# Copyright 2025 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from datetime import timedelta

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleIntervalSpec,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleState,
)

from maascommon.workflows.dns import CONFIGURE_DNS_WORKFLOW_NAME

SCHEDULES = {
    # Do NOT update the schedule definition here. ALWAYS change the name so that the old definition is dropped and the new one
    # is recreated.
    CONFIGURE_DNS_WORKFLOW_NAME: Schedule(
        action=ScheduleActionStartWorkflow(
            CONFIGURE_DNS_WORKFLOW_NAME,
            id=CONFIGURE_DNS_WORKFLOW_NAME,
            task_queue="region",
        ),
        policy=SchedulePolicy(overlap=ScheduleOverlapPolicy.SKIP),
        spec=ScheduleSpec(
            intervals=[ScheduleIntervalSpec(every=timedelta(minutes=1))]
        ),
        state=ScheduleState(note="Autorefresh DNS."),
    )
}


async def register_schedules(temporal_client: Client):
    """
    Reconcile expected schedules with the Temporal server.

    1. Remove dropped schedules:
       If a schedule exists in Temporal but is no longer present in
       the local `SCHEDULES` dictionary, it is deleted from Temporal.

    2. Register missing schedules:
       If a schedule is defined locally in `SCHEDULES` but does not
       yet exist in Temporal, it is created.
    """

    _expected_schedules = set(SCHEDULES.keys())
    _registered_schedules = set()
    async for schedule in await temporal_client.list_schedules():
        _registered_schedules.add(schedule.id)

    _schedules_to_delete = _registered_schedules - _expected_schedules
    for schedule in _schedules_to_delete:
        handle = temporal_client.get_schedule_handle(schedule)
        await handle.delete()

    _schedules_to_add = _expected_schedules - _registered_schedules
    for schedule in _schedules_to_add:
        await temporal_client.create_schedule(schedule, SCHEDULES[schedule])
