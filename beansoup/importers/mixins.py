"""Mixins for importer classes."""


class FilterChain:
    """A mixin to pass imported entries through a pipeline of filters.

    This mixin modifies the extract method of a concrete instance of
    ImporterProtocol to run the extracted entries through a chain of
    arbitrary filters.
    """
    def __init__(self, *args, **kwargs):
        """Set up the filter chain and pass the rest of the arguments to the
        base class.

        Args:
          filters: A list of callables taking a list of entries and returning
            a subset of them.
        """
        self.filters = kwargs.pop('filters', [])
        super(FilterChain, self).__init__(*args, **kwargs)

    def extract(self, file):
        """Extract the entries using the main importer and then run all
        the filters on them.
        """
        entries = super(FilterChain, self).extract(file)
        for filter in self.filters:
            entries = filter(entries)
        return entries
