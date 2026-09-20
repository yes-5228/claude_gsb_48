"""Flask CLI commands: flask init-db / seed / reset-db."""
import click

from .extensions import db
from .models import Area, AreaMembership, Exceedance, Measurement, Person, Station


def register_commands(app):
    @app.cli.command("init-db")
    def init_db():
        """Create database tables."""
        db.create_all()
        click.echo("数据库表已创建")

    @app.cli.command("seed")
    @click.option("--days", default=5, show_default=True, help="生成最近多少天的数据")
    @click.option("--force", is_flag=True, help="已有数据时仍然追加写入")
    def seed(days, force):
        """Load demo stations and monitoring records."""
        from .seed import seed_demo_data

        if Station.query.count() and not force:
            click.echo("已存在监测点数据, 如确需追加请使用 --force")
            return
        db.create_all()
        totals = seed_demo_data(days=days)
        click.echo(
            "演示数据写入完成: 监测点 %(stations)s 个, 监测数据 %(measurements)s 条, "
            "超标记录 %(exceedances)s 条" % totals
        )

    @app.cli.command("reset-db")
    @click.option("--with-demo/--empty", default=True, help="是否写入演示数据")
    def reset_db(with_demo):
        """Drop all tables, recreate them and optionally load demo data."""
        from .seed import reset_database, seed_demo_data

        reset_database()
        click.echo("数据库已重置")
        if with_demo:
            totals = seed_demo_data()
            click.echo("演示数据写入完成: %s" % totals)

    @app.cli.command("stats")
    def stats():
        """Print a short record summary."""
        click.echo(
            "片区 %d 个 / 责任人 %d 人 / 监测点 %d 个 / 监测数据 %d 条 / 超标记录 %d 条"
            % (
                Area.query.count(),
                Person.query.count(),
                Station.query.count(),
                Measurement.query.count(),
                Exceedance.query.count(),
            )
        )

    @app.cli.command("backfill-areas")
    def backfill_areas():
        """Backfill area + assignment rows for stations created before area management."""
        from .services import area_service

        changed = area_service.backfill_station_areas()
        click.echo("片区归属回填完成, 补建归属记录 %d 条" % changed)
