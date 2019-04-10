"""
Settings overrides for Figures in LMS/Production (aka AWS).
"""
import os
from celery.schedules import crontab


def update_webpack_loader(webpack_loader_settings, figures_env_tokens):
    """
    Update the WEBPACK_LOADER in the settings.
    """
    # Specify the 'figures' package directory
    figures_app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Define our webpack asset bundling constants
    webpack_stats_file = figures_env_tokens.get('WEBPACK_STATS_FILE', 'webpack-stats.json')
    webpack_stats_full_path = os.path.abspath(os.path.join(figures_app_dir, webpack_stats_file))
    webpack_loader_settings.update(FIGURES_APP={
        'BUNDLE_DIR_NAME': 'figures/',
        'STATS_FILE': webpack_stats_full_path,
    })


def update_celerybeat_schedule(celerybeat_schedule_settings, figures_env_tokens):
    """
    Figures pipeline job schedule configuration in CELERYBEAT_SCHEDULE.
    """
    if figures_env_tokens.get('ENABLE_DAILY_METRICS_IMPORT', True):
        celerybeat_schedule_settings['figures-populate-daily-metrics'] = {
            'task': 'figures.tasks.populate_daily_metrics',
            'schedule': crontab(
                hour=figures_env_tokens.get('DAILY_METRICS_IMPORT_HOUR', 2),
                minute=figures_env_tokens.get('DAILY_METRICS_IMPORT_MINUTE', 0),
                ),
            }


def plugin_settings(settings):
    """
    Update the LMS/Production (aka AWS) settings to use Figures properly.


    Adds entries to the environment settings

    You can disable CeleryBeat scheduler for Figures by configuration the
    ``lms.env.json`` file.

    Create or update ``FIGURES`` as a top level key in
    the ``lms.env.json`` file:

    ::

        "FIGURES": {
            "ENABLE_DAILY_METRICS_IMPORT": false
        },

    """
    settings.ENV_TOKENS.setdefault('FIGURES', {})
    update_webpack_loader(settings.WEBPACK_LOADER, settings.ENV_TOKENS['FIGURES'])
    update_celerybeat_schedule(settings.CELERYBEAT_SCHEDULE, settings.ENV_TOKENS['FIGURES'])
