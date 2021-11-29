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
    """Some example content."""
    sponsor_message = Table.grid(padding=1)
    sponsor_message.add_column(justify="right", style="dim")
    sponsor_message.add_column(no_wrap=True)
    for key, value in data['layout_info'].items():
        sponsor_message.add_row(f"{key}", f"[yellow]{value}")

    message_panel = Panel(
        Align.center(
            Group(Align.center(sponsor_message)),
            vertical="middle"
        ),
        box=box.ROUNDED,
        padding=(1, 2),
        title=f"[b red]{data['layout_info']['Server IP']}",
        border_style="bright_blue",
    )
    return message_panel


def layout_peggy(data) -> Panel:
    """Some example content."""
    sponsor_message = Table.grid(padding=1)
    sponsor_message.add_column(justify="left", style="dim")
    sponsor_message.add_column(no_wrap=True)
    for key, value in data.items():
        sponsor_message.add_row(f"{key}", f"[yellow]{value}")

    message_panel = Panel(
        Align.center(
            Group(Align.center(sponsor_message)),
            vertical="middle"
        ),
        box=box.ROUNDED,
        padding=(1, 2),
        title=f"[b red]PEGGY module state stats",
        border_style="bright_blue",
    )
    return message_panel


def layout_body(uptime):
    # block, response = get_uptime()
    # # count = response.count(VALIDATOR_ADDR)
    # status = '[magenta]✗ ', '[green]✓ ', '[cyan]:rocket: '
    # count = response.count(VALIDATOR_ADDR)
    # if f"{status[count]}{block}" not in UPTIME:
    #     UPTIME.append(f"{status[count]}{block}")

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
    # table.add_row(f"test {UPTIME[-1]}")

    columns = Columns(reversed(tables), padding=0, expand=True, align='center')

    return columns


layout.split(
    Layout(name="header", size=1),
    Layout(ratio=1, name="main"),
    Layout(size=5, name="footer"),
    # Layout(size=5, name="footer1"),
)

layout["main"].split_row(Layout(name="INFO"), Layout(name="body", ratio=2))
layout["footer"].split_row(
    Layout(name="HEIGHT"),
    Layout(name="Voting_Power"),
    Layout(name="Catching_up"),
    Layout(name="Peers"),
    Layout(name="Active_vals"),
    Layout(name="Rewards"),
)

layout['body'].split_row(Layout(name='colored_blocks'), Layout(name='peggy'))
# layout['body'].split_row(Layout(name='colored_blocks'))


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
