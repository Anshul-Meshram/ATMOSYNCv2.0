from alembic import op
import sqlalchemy as sa


revision = "001_create_weather_observations"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "weather_observations",

        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(),
            primary_key=True,
            nullable=False,
        ),

        sa.Column(
            "climate_identifier",
            sa.String(length=32),
            nullable=False,
        ),

        sa.Column(
            "observation_date",
            sa.Date(),
            nullable=False,
        ),

        sa.Column("mean_temperature", sa.Numeric()),
        sa.Column("mean_temperature_flag", sa.String(length=8)),

        sa.Column("min_temperature", sa.Numeric()),
        sa.Column("min_temperature_flag", sa.String(length=8)),

        sa.Column("max_temperature", sa.Numeric()),
        sa.Column("max_temperature_flag", sa.String(length=8)),

        sa.Column("total_precipitation", sa.Numeric()),
        sa.Column(
            "total_precipitation_flag",
            sa.String(length=8),
        ),

        sa.Column("total_rain", sa.Numeric()),
        sa.Column("total_rain_flag", sa.String(length=8)),

        sa.Column("total_snow", sa.Numeric()),
        sa.Column("total_snow_flag", sa.String(length=8)),

        sa.Column("snow_on_ground", sa.Numeric()),
        sa.Column("snow_on_ground_flag", sa.String(length=8)),

        sa.Column("direction_max_gust", sa.Numeric()),
        sa.Column(
            "direction_max_gust_flag",
            sa.String(length=8),
        ),

        sa.Column("speed_max_gust", sa.Numeric()),
        sa.Column("speed_max_gust_flag", sa.String(length=8)),

        sa.Column("cooling_degree_days", sa.Numeric()),
        sa.Column(
            "cooling_degree_days_flag",
            sa.String(length=8),
        ),

        sa.Column("heating_degree_days", sa.Numeric()),
        sa.Column(
            "heating_degree_days_flag",
            sa.String(length=8),
        ),

        sa.Column("min_relative_humidity", sa.Numeric()),
        sa.Column(
            "min_relative_humidity_flag",
            sa.String(length=8),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "climate_identifier",
            "observation_date",
            name="uq_weather_observation",
        ),
    )


def downgrade() -> None:
    op.drop_table("weather_observations")
