from rich import box
from datetime import datetime
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.layout import Layout
from rich.console import Group
from rich.columns import Columns

layout = Layout()


def layout_info(data) -> Panel:
    message = Table.grid(padding=1)
    message.add_column(justify="left", style="dim")
    message.add_column(no_wrap=True)

    if 'layout_info' in data:
        for key, value in data['layout_info'].items():
            message.add_row(f"{key}", f"[yellow]{value}")

        if 'Server IP' not in data['layout_info']:
            title = data['layout_info']['Moniker']
        else:
            title = f"[b red]{data['layout_info']['Server IP']}"

    if 'bridge_chain' in data:
        title = f"[b red]PEGGO module stats"
        for key, value in data.items():
            message.add_row(f"{key}", f"[yellow]{value}")

    message_panel = Panel(
        Align.center(
            Group(Align.center(message)),
            vertical="middle"
        ),
        box=box.ROUNDED,
        padding=(1, 2),
        title=title,
        border_style="bright_blue",
    )
    return message_panel


def layout_body(uptime):

    tables = []

    for i in uptime[-200:]:
        table = Table(
            style="green",
            row_styles=["none", "dim"],
            show_header=False,
            box=box.ROUNDED,
            padding=0)

        table.add_row(i)
        tables.append(Align.center(table))

    columns = Columns(reversed(tables), padding=0, expand=True, align='center')

    return columns


layout.split(
    Layout(name="header", size=1),
    Layout(ratio=1, name="main"),
    Layout(size=5, name="footer"),
)

layout["main"].split_row(Layout(name="INFO"), Layout(name="body", ratio=2))
layout["INFO"].split_column(Layout(name="val_info", ratio=4), Layout(name="delegator_txs"))
layout["footer"].split_row(
    Layout(name="HEIGHT"),
    Layout(name="Voting_Power"),
    Layout(name="BOND_STATUS"),
    Layout(name="Catching_up"),
    Layout(name="Peers"),
    Layout(name="Active_vals"),
    Layout(name="Block_counter"),
    Layout(name="Active_proposals"),
    Layout(name="Rewards"),
)

layout['body'].split_row(Layout(name='colored_blocks'), Layout(name='peggo'))

layout['colored_blocks'].split_column(
    Layout(name="blocks", ratio=4),
    Layout(name="umee_orch_txs")
)

layout['peggo'].split_column(
    Layout(name="peggo_state", ratio=4),
    Layout(name="etherscan_txs")
)


class Clock:
    """Renders the time in the center of the screen."""

    def __rich__(self) -> Text:
        return Text(datetime.now().ctime(),
                    style="bold magenta",
                    justify="center")


layout["header"].update(Clock())


def footer(data, title) -> Panel:
    footer_panel = Panel(
        Align.center(Group(Align.center(data)), vertical="middle"),
        box=box.ROUNDED,
        # padding=(1, 2),
        title=f"[b cyan]{title}",
        border_style="bright_blue",
    )
    return footer_panel
