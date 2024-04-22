from django.test.runner import DiscoverRunner


class ProductionDBTestRunner(DiscoverRunner):
    """This runner executes queries against the production database."""

    def setup_databases(self, **kwargs):
            pass

    def teardown_databases(self, old_config, **kwargs):
        pass
