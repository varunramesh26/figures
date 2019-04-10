'''

For these tests, we need to build at least one set of data that includes

* Data for a set of days that include data points both before, during, and after
  each time period for which we test
* Models populated:
** CourseOverview
** CourseEnrollment
** StudentModule
** CourseDailyMetrics
** SiteDailyMetrics
** User
** UserProfile

Initially:
* we need to test for when the date_for is the current date
* We are going to do minimal testing just to make sure the functions can be
  called succesfully. Correctness checking to follow


# Multisite support in testing

The tests in this module were initially written for single site instances.
To provide multisite coverage, we created two test classes from each original.
One test class to setup data for standalone mode and aonther test class to setup
data for multisite mode. This results in duplicate code, but saves significant
time to add multisite coverage. At some point we'll need to address testing tech
debt, at which point we'll address the maintainability of this test module


# TODOs

Improve the time performance of these tests. We're currently generating
a rather large set of time series data. We probably want to create a separate
test suite so that we can do much more robust data validation with bigger time
series sets

'''
import datetime

from dateutil.rrule import rrule, DAILY
import mock
import pytest

from django.contrib.sites.models import Site
from django.utils.timezone import utc

import organizations

from figures import metrics
import figures.helpers
import figures.sites

from tests.factories import (
    CourseDailyMetricsFactory,
    CourseOverviewFactory,
    OrganizationFactory,
    OrganizationCourseFactory,
    SiteDailyMetricsFactory,
    SiteFactory,
    StudentModuleFactory,
    UserFactory,
    )
from tests.helpers import organizations_support_sites

# TODO:

# - build set of User, StudentModule, CourseOverview objects to test the
# StudentModule based methods and classes

# Test with a date range where there is at least one month in the middle
DEFAULT_START_DATE = datetime.datetime(2018, 1, 1, 0, 0, tzinfo=utc)
DEFAULT_END_DATE = datetime.datetime(2018, 3, 1, 0, 0, tzinfo=utc)


def add_user_to_site(user, site):
    orgs = figures.sites.get_organizations_for_site(site)
    assert orgs.count() == 1, 'requires a single org for the site. Found {}'.format(
        orgs.count())
    if not organizations.models.UserOrganizationMapping.objects.filter(
        user=user, organization=orgs.first()).exists():
        obj, created = organizations.models.UserOrganizationMapping.objects.get_or_create(
            user=user,
            organization=orgs[0],
            # defaults=dict(is_active=True, is_amc_admin=False),
        )
        return obj, created

def add_course_to_site(course_id, site):
    orgs = figures.sites.get_organizations_for_site(site)
    assert orgs.count() == 1, 'requires a single org for the site. Found {}'.format(
        orgs.count())
    if not organizations.models.OrganizationCourse.objects.filter(
        course_id=str(course_id), organization=orgs.first()).exists():
        obj, created = organizations.models.OrganizationCourse.objects.get_or_create(
            course_id=str(course_id),
            organization=orgs[0],
        )
        return obj, created

def create_student_module_test_data(start_date, end_date):
    '''

    NOTE: There are many combinations of unique students, courses, and student
    state. We're going to start with a relatively simple set

    1. A single course
    2. A single set per student (learner)
    3. a small number of students to reduce test run time

    If we create a record per day then we can work off of a unique datapoint
    per day
    '''
    student_modules = []
    user = UserFactory()
    course_overview = CourseOverviewFactory()

    for dt in rrule(DAILY, dtstart=start_date, until=end_date):
        student_modules.append(StudentModuleFactory(
            student=user,
            course_id=course_overview.id,
            created=dt,
            modified=dt,
            ))

    # we'll return everything we create
    return dict(
        user=user,
        course_overview=course_overview,
        student_modules=student_modules,
    )


def create_site_daily_metrics_data(site, start_date, end_date):
    '''
    NOTE: We can generalize this and the `create_course_daily_metrics_data`
    function with considering that the course mertrics creation method can
    assign a course id. When we become site-aware, then the site metrics will
    also need to be able to assign a site identifier
    '''
    def incr_func(key):
        return dict(
            cumulative_active_user_count=2,
            todays_active_user_count=2,
            total_user_count=5,
            course_count=1,
            total_enrollment_count=3,
        ).get(key, 0)

    # Initial values
    data = dict(
        cumulative_active_user_count=50,
        todays_active_user_count=10,
        total_user_count=5,
        course_count=5,
        total_enrollment_count=100,
    )
    metrics = []
    for dt in rrule(DAILY, dtstart=start_date, until=end_date):
        metrics.append(SiteDailyMetricsFactory(
            date_for=dt,
            site=site,
            **data))
        data.update(
            {key: val + incr_func(key) for key, val in data.iteritems()})
    return metrics


def create_course_daily_metrics_data(site, start_date, end_date, course_id=None):
    '''
    Creates a daily sequence of CourseDailyMetrics objects

    If course_id is provided as a parameter, then all CourseDailyMetrics objects
    will have that course_id. This is useful for testing time series for a
    specific course. Otherwise FactoryBoy assigns the course id in the
    ``tests.factories`` module
    '''
    # Initial values
    data = dict(
        enrollment_count=2,
        active_learners_today=1,
        average_progress=0.5,
        average_days_to_complete=10,
        num_learners_completed=3
    )
    # keys and the values to increment by
    incr_data = dict(
        enrollment_count=3,
        active_learners_today=2,
        average_progress=0,
        average_days_to_complete=0,
        num_learners_completed=1
    )

    if course_id:
        data['course_id'] = course_id
    metrics = []
    for dt in rrule(DAILY, dtstart=start_date, until=end_date):
        metrics.append(CourseDailyMetricsFactory(
            date_for=dt,
            site=site,
            **data))
        # This only updates the keys that are present in the incr_data dict
        data.update(
            {key: data[key] + incr_data[key] for key in incr_data.keys()})
    return metrics


def create_users_joined_over_time(site, is_multisite, start_date, end_date):
    '''
    creates users. Each user joins on a succesive date between the dates
    pass as arguments
    '''
    users = []
    for dt in rrule(DAILY, dtstart=start_date, until=end_date):
        user = UserFactory(date_joined=dt)
        if is_multisite:
            add_user_to_site(user=user, site=site)
        users.append(user)
    return users


@pytest.mark.django_db
class TestGetMonthlySiteMetrics(object):
    '''
    This test also exercises the time period getters used in
    metrics.get_monthly_site_metrics
    '''
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.today = datetime.datetime(2018, 1, 6, tzinfo=utc)
        self.site_daily_metrics = None
        self.expected_keys = (
            'monthly_active_users',
            'total_site_users',
            'total_site_courses',
            'total_course_enrollments',
            'total_course_completions',)

    @pytest.mark.skip(reason='Test not implemented yet')
    # @pytest.mark.paramtrize('date_for', [
    #     (None),
    #     (self.today),
    #     ])
    def test_get_today(self):
        date_for = self.today
        data = metrics.get_monthly_site_metrics(date_for=date_for)
        assert set(data.keys()) == self.expected_keys


@pytest.mark.django_db
class TestGetMonthlyActiveUsers(object):

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.site_daily_metrics = None

    @pytest.mark.skip(reason='Test not implemented yet')
    def test_get(self):
        pass


@pytest.mark.django_db
class TestSiteMetricsGettersStandalone(object):
    """
    This class tests the figures.metrics module functions in standalone mode

    TODO: Pull out the start/end date setup into a 'TimeSeriesTest' base class
    """
    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        settings.FEATURES['FIGURES_IS_MULTISITE'] = False
        assert not figures.helpers.is_multisite()
        assert Site.objects.count() == 1
        self.site = Site.objects.first()
        self.data_start_date = DEFAULT_START_DATE
        self.data_end_date = DEFAULT_END_DATE
        self.features = {'FIGURES_IS_MULTISITE': False}
        self.site_daily_metrics = create_site_daily_metrics_data(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)

    def test_get_active_users_for_time_period(self):

        student_module_sets = []
        for i in range(0, 3):
            data = create_student_module_test_data(
                    start_date=self.data_start_date,
                    end_date=self.data_end_date)
            student_module_sets.append(data)

        count = metrics.get_active_users_for_time_period(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)
        assert count == len(student_module_sets)

    def test_get_total_site_users_for_time_period(self):
        '''
        TODO: add users who joined before and after the time period, and
        compare the count to the users created on or before the end date

        TODO: Create
        '''
        users = create_users_joined_over_time(
            site=self.site,
            is_multisite=figures.helpers.is_multisite(),
            start_date=self.data_start_date,
            end_date=self.data_end_date)
        count = metrics.get_total_site_users_for_time_period(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            calc_raw=True,
            )
        assert count == len(users)

    def test_get_total_site_users_joined_for_time_period(self):
        '''
        TODO: add users who joined before and after the time period, and
        compare the count to the users created within the time period
        '''
        users = create_users_joined_over_time(
            site=self.site,
            is_multisite=figures.helpers.is_multisite(),
            start_date=self.data_start_date,
            end_date=self.data_end_date)
        count = metrics.get_total_site_users_joined_for_time_period(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)
        assert count == len(users)

    def test_get_total_enrollments_for_time_period(self):
        '''
        We're incrementing values for test data, so the last SiteDailyMetrics
        record will have the max value
        '''
        count = metrics.get_total_enrollments_for_time_period(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)

        assert count == self.site_daily_metrics[-1].total_enrollment_count

    def test_get_total_site_courses_for_time_period(self):
        '''
        We're incrementing values for test data, so the last SiteDailyMetrics
        record will have the max value
        '''
        count = metrics.get_total_site_courses_for_time_period(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)

        assert count == self.site_daily_metrics[-1].course_count

    def test_get_total_course_completions_for_time_period(self):
        '''
        We're incrementing values for test data, so the last SiteDailyMetrics
        record will have the max value
        '''

        cdm = create_course_daily_metrics_data(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)
        count = metrics.get_total_course_completions_for_time_period(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)
        assert count == cdm[-1].num_learners_completed

    def test_get_monthly_site_metrics(self):
        '''
        Since we are testing results for individual getters in other test
        methods in this class, our prime goal is to ensure proper structure
        '''
        expected_top_lvl_keys = [
            'total_site_users',
            'total_course_completions',
            'total_course_enrollments',
            'total_site_courses',
            'monthly_active_users'
        ]
        expected_2nd_lvl_keys = ['current_month', 'history']
        expected_history_elem_keys = ['period', 'value']
        actual = metrics.get_monthly_site_metrics(site=self.site)

        assert set(actual.keys()) == set(expected_top_lvl_keys)
        for key, val in actual.iteritems():
            assert set(val.keys()) == set(expected_2nd_lvl_keys)
            assert len(val['history']) > 0
            assert set(val['history'][0].keys()) == set(expected_history_elem_keys)


@pytest.mark.skipif(not organizations_support_sites(),
                    reason='Organizations support sites')
# @mock.patch('figures.settings.features', return_value={'FIGURES_IS_MULTISITE': True})
@pytest.mark.django_db
class TestSiteMetricsGettersMultisite(object):
    '''The purpose of this class is to test the individual time period getter
    functions

    TODO: Pull out the start/end date setup into a 'TimeSeriesTest' base class
    '''
    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        settings.FEATURES['FIGURES_IS_MULTISITE'] = True
        is_multisite = figures.helpers.is_multisite()
        assert is_multisite
        self.data_start_date = DEFAULT_START_DATE
        self.data_end_date = DEFAULT_END_DATE

        self.alpha_site = SiteFactory(domain='alpha.site')
        self.alpha_org =  OrganizationFactory(sites=[self.alpha_site])
        self.alpha_site_daily_metrics = create_site_daily_metrics_data(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)

        self.bravo_site = SiteFactory(domain='bravo.site')
        self.bravo_org =  OrganizationFactory(sites=[self.bravo_site])
        self.bravo_site_daily_metrics = create_site_daily_metrics_data(
            site=self.bravo_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)

    def test_get_active_users_for_time_period(self):
        '''

        '''
        assert figures.helpers.is_multisite()
        student_module_sets = []
        for i in range(0, 3):
            data = create_student_module_test_data(
                    start_date=self.data_start_date,
                    end_date=self.data_end_date)
            student_module_sets.append(data)
            uom, created = add_user_to_site(user=data['user'], site=self.alpha_site)
            # add course to site
            org_course, created = add_course_to_site(
                data['course_overview'].id,
                site=self.alpha_site)
        count = metrics.get_active_users_for_time_period(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)

        assert count == len(student_module_sets)

    def test_get_total_site_users_for_time_period(self):
        '''
        TODO: add users who joined before and after the time period, and
        compare the count to the users created on or before the end date

        TODO: Create
        '''
        users = create_users_joined_over_time(
            site=self.alpha_site,
            is_multisite=figures.helpers.is_multisite(),
            start_date=self.data_start_date,
            end_date=self.data_end_date)
        count = metrics.get_total_site_users_for_time_period(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            calc_raw=True,
            )
        assert count == len(users)

    def test_get_total_site_users_joined_for_time_period(self):
        '''
        TODO: add users who joined before and after the time period, and
        compare the count to the users created within the time period
        '''
        users = create_users_joined_over_time(
            site=self.alpha_site,
            is_multisite=figures.helpers.is_multisite(),
            start_date=self.data_start_date,
            end_date=self.data_end_date)
        count = metrics.get_total_site_users_joined_for_time_period(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)
        assert count == len(users)

    def test_get_total_enrollments_for_time_period(self):
        '''
        We're incrementing values for test data, so the last SiteDailyMetrics
        record will have the max value
        '''
        count = metrics.get_total_enrollments_for_time_period(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)

        assert count == self.alpha_site_daily_metrics[-1].total_enrollment_count

    def test_get_total_site_courses_for_time_period(self):
        '''
        We're incrementing values for test data, so the last SiteDailyMetrics
        record will have the max value
        '''
        count = metrics.get_total_site_courses_for_time_period(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)

        assert count == self.alpha_site_daily_metrics[-1].course_count

    def test_get_total_course_completions_for_time_period(self):
        '''
        We're incrementing values for test data, so the last SiteDailyMetrics
        record will have the max value
        '''

        cdm = create_course_daily_metrics_data(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)
        count = metrics.get_total_course_completions_for_time_period(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date)
        assert count == cdm[-1].num_learners_completed

    def test_get_monthly_site_metrics(self):
        '''
        Since we are testing results for individual getters in other test
        methods in this class, our prime goal is to ensure proper structure
        '''
        expected_top_lvl_keys = [
            'total_site_users',
            'total_course_completions',
            'total_course_enrollments',
            'total_site_courses',
            'monthly_active_users'
        ]
        expected_2nd_lvl_keys = ['current_month', 'history']
        expected_history_elem_keys = ['period', 'value']
        actual = metrics.get_monthly_site_metrics(site=self.alpha_site)

        assert set(actual.keys()) == set(expected_top_lvl_keys)
        for key, val in actual.iteritems():
            assert set(val.keys()) == set(expected_2nd_lvl_keys)
            assert len(val['history']) > 0
            assert set(val['history'][0].keys()) == set(expected_history_elem_keys)


@pytest.mark.django_db
class TestCourseMetricsGettersStandalone(object):
    '''
    Test the metrics functions that retrieve metrics for a specific course over
    a time series

    Refactoring: Given the similarity of the tests in this class, we may be able
    to parametrize based on the statistic (Max, Avg, Sum):
        * method under test
        * model attribute for which we are comparing
        * statistic type

    If we do that, then we can also create a generalized/abstract test class and
    inherit from it for our concrete tests. This will be especially useful when
    we eventually refactor Figures to generalize metrics models to allow storage
    of data provided externally (like plug-ins or remote APIs).

    An assumption for validating against expected values is that the test data
    increments values over time so that the last record in
    self.course_daily_metrics contains the maximum value. This of course won't
    work for averaged metrics
    '''
    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        settings.FEATURES['FIGURES_IS_MULTISITE'] = False
        is_multisite = figures.helpers.is_multisite()
        assert not is_multisite
        assert Site.objects.count() == 1
        self.site = Site.objects.first()
        self.data_start_date = DEFAULT_START_DATE
        self.data_end_date = DEFAULT_END_DATE
        self.features = {'FIGURES_IS_MULTISITE': False}
        self.course_overview = CourseOverviewFactory()
        self.course_daily_metrics = create_course_daily_metrics_data(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            course_id=self.course_overview.id)

    def get_average(self, attribute, val_type):
        data = [getattr(rec, attribute) for rec in self.course_daily_metrics]
        return sum(data)/val_type(len(data))

    def test_get_course_enrolled_users_for_time_period(self):
        '''
        Validates results against the max value for the metrics model attribute
        '''
        expected = self.course_daily_metrics[-1].enrollment_count
        actual = metrics.get_course_enrolled_users_for_time_period(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            course_id=self.course_overview.id)
        assert actual == expected

    def test_get_course_average_progress_for_time_period(self):
        actual = metrics.get_course_average_progress_for_time_period(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            course_id=self.course_overview.id)
        assert actual == self.get_average('average_progress', float)

    def test_get_course_average_days_to_complete_for_time_period(self):
        actual = metrics.get_course_average_days_to_complete_for_time_period(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            course_id=self.course_overview.id)
        assert actual == self.get_average('average_days_to_complete', int)

    def test_get_course_num_learners_completed_for_time_period(self):
        expected = max(
            [rec.num_learners_completed for rec in self.course_daily_metrics])
        actual = metrics.get_course_num_learners_completed_for_time_period(
            site=self.site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            course_id=self.course_overview.id)
        assert actual == expected


@pytest.mark.skipif(not organizations_support_sites(),
                    reason='Organizations support sites')
@pytest.mark.django_db
class TestCourseMetricsGettersMultisite(object):
    '''
    Test the metrics functions that retrieve metrics for a specific course over
    a time series

    Refactoring: Given the similarity of the tests in this class, we may be able
    to parametrize based on the statistic (Max, Avg, Sum):
        * method under test
        * model attribute for which we are comparing
        * statistic type

    If we do that, then we can also create a generalized/abstract test class and
    inherit from it for our concrete tests. This will be especially useful when
    we eventually refactor Figures to generalize metrics models to allow storage
    of data provided externally (like plug-ins or remote APIs).

    An assumption for validating against expected values is that the test data
    increments values over time so that the last record in
    self.course_daily_metrics contains the maximum value. This of course won't
    work for averaged metrics
    '''
    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        """
        TODO: rework this so we have a top level object as a dict, then we can
        swap the sites in and out to test inclusion and exclusion
        """
        settings.FEATURES['FIGURES_IS_MULTISITE'] = True
        is_multisite = figures.helpers.is_multisite()
        assert is_multisite
        self.data_start_date = DEFAULT_START_DATE
        self.data_end_date = DEFAULT_END_DATE
        self.alpha_site = SiteFactory(domain='alpha.site')
        self.alpha_course_overview = CourseOverviewFactory()
        self.alpha_course_daily_metrics = create_course_daily_metrics_data(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            course_id=self.alpha_course_overview.id)

        self.bravo_site = SiteFactory(domain='bravo.site')
        self.bravo_course_overview = CourseOverviewFactory()
        self.bravo_course_daily_metrics = create_course_daily_metrics_data(
            site=self.bravo_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            course_id=self.bravo_course_overview.id)

    def get_average(self, course_daily_metrics, attribute, val_type):
        data = [getattr(rec, attribute) for rec in course_daily_metrics]
        return sum(data)/val_type(len(data))

    def test_get_course_enrolled_users_for_time_period(self):
        '''
        Validates results against the max value for the metrics model attribute
        '''
        expected = self.alpha_course_daily_metrics[-1].enrollment_count
        actual = metrics.get_course_enrolled_users_for_time_period(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            course_id=self.alpha_course_overview.id)
        assert actual == expected

    def test_get_course_average_progress_for_time_period(self):
        actual = metrics.get_course_average_progress_for_time_period(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            course_id=self.alpha_course_overview.id)
        assert actual == self.get_average(self.alpha_course_daily_metrics,
            'average_progress', float)

    def test_get_course_average_days_to_complete_for_time_period(self):
        actual = metrics.get_course_average_days_to_complete_for_time_period(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            course_id=self.alpha_course_overview.id)
        assert actual == self.get_average(self.alpha_course_daily_metrics,
            'average_days_to_complete', int)

    def test_get_course_num_learners_completed_for_time_period(self):
        expected = max(
            [rec.num_learners_completed for rec in self.alpha_course_daily_metrics])
        actual = metrics.get_course_num_learners_completed_for_time_period(
            site=self.alpha_site,
            start_date=self.data_start_date,
            end_date=self.data_end_date,
            course_id=self.alpha_course_overview.id)
        assert actual == expected
