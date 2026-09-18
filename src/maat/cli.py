import click
from maat.modes.ask import ask_mode
from maat.modes.research import research_mode
from maat.modes.file import file_mode

@click.group()
def cli():
    """House of Ma'at — legal research and filing assistant."""
    pass

@cli.command()
@click.argument('question')
@click.option('--sources', default='all', help='Sources to query: all, maat, blacks, courtlistener')
def ask(question, sources):
    """Answer a legal question with citations."""
    click.echo(ask_mode(question, sources))

@cli.command()
@click.argument('topic')
@click.option('--jurisdiction', default='', help='Limit to a jurisdiction, e.g. Indiana')
@click.option('--year-min', type=int, default=None)
@click.option('--year-max', type=int, default=None)
def research(topic, jurisdiction, year_min, year_max):
    """Find verified cases on a topic."""
    click.echo(research_mode(topic, jurisdiction, year_min, year_max))

@cli.command()
@click.option('--type', 'case_type', required=True, help='Motion/complaint/answer type')
@click.option('--evidence', required=True, type=click.Path(exists=True), help='Path to evidence folder')
@click.option('--output', default='./output', type=click.Path())
def file(case_type, evidence, output):
    """Draft a filing packet from evidence."""
    click.echo(file_mode(case_type, evidence, output))

def main():
    cli()

if __name__ == '__main__':
    main()
