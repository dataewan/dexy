from dexy.task import Task
import dexy.artifact
import dexy.exceptions
import dexy.filter
import fnmatch
import os

class Doc(Task):
    """
    A single file + 0 or more filters applied to that file.
    """
    @classmethod
    def filter_class_for_alias(klass, alias):
        if alias == '':
            raise dexy.exceptions.BlankAlias
        else:
            return dexy.filter.Filter.aliases[alias]

    def output(self):
        """
        Returns a reference to the output_data Data object generated by the final filter.
        """
        return self.final_artifact.output_data

    def setup_initial_artifact(self):
        if os.path.exists(self.name):
            initial = dexy.artifact.InitialArtifact(self.name, wrapper=self.wrapper)
        else:
            initial = dexy.artifact.InitialVirtualArtifact(self.name, wrapper=self.wrapper)

        initial.args = self.args
        initial.name = self.name
        initial.prior = None
        initial.doc = self
        initial.created_by_doc = self.created_by_doc

        self.children.append(initial)
        self.artifacts.append(initial)
        self.final_artifact = initial

    def setup_filter_artifact(self, key, filters):
        artifact = dexy.artifact.FilterArtifact(key, wrapper=self.wrapper)
        artifact.args = self.args
        artifact.doc = self
        artifact.filter_alias = filters[-1]
        artifact.doc_filepath = self.name
        artifact.prior = self.artifacts[-1]
        artifact.created_by_doc = self.created_by_doc

        try:
            artifact.filter_class = self.filter_class_for_alias(filters[-1])
        except dexy.exceptions.BlankAlias:
            raise dexy.exceptions.UserFeedback("You have a trailing | or you have 2 | symbols together in your specification for %s" % self.key)

        if not artifact.filter_class.is_active():
            raise dexy.exceptions.InactiveFilter

        artifact.next_filter_alias = None
        artifact.next_filter_class = None
        artifact.next_filter_name = None

        if len(filters) < len(self.filters):
            next_filter_alias = self.filters[len(filters)]
            artifact.next_filter_alias = next_filter_alias
            artifact.next_filter_class = self.filter_class_for_alias(next_filter_alias)
            artifact.next_filter_name = artifact.next_filter_class.__name__

        self.children.append(artifact)
        self.artifacts.append(artifact)
        self.final_artifact = artifact
        self.metadata = artifact.metadata

    def setup_child_docs(self):
        """
        Make sure all child Doc instances are setup also.
        """
        for child in self.children:
            if not child in self.artifacts:
                if child.state == 'new':
                    child.wrapper = self.wrapper
                    child.setup()

    def setup(self):
        self.set_log()

        self.name = self.key.split("|")[0]
        self.filters = self.key.split("|")[1:]
        self.artifacts = []

        self.setup_initial_artifact()

        for i in range(0,len(self.filters)):
            filters = self.filters[0:i+1]
            key = "%s|%s" % (self.name, "|".join(filters))
            self.setup_filter_artifact(key, filters)

        self.setup_child_docs()
        self.after_setup()

class WalkDoc(Task):
    """
    Parent class for docs which walk Dexy project directories.

    Shares code for skipping dexy directories.
    """
    def walk(self, start, exclude_at_root, exclude_everywhere):
        # TODO implement exclude_everywhere
        for dirpath, dirnames, filenames in os.walk(start):
            if dirpath == ".":
                for x in exclude_at_root:
                    if x in dirnames:
                        dirnames.remove(x)

            for filename in filenames:
                yield(dirpath, filename)

class PatternDoc(WalkDoc):
    """
    A doc which takes a file matching pattern and creates individual Doc objects for all files that match the pattern.
    """
    def setup(self):
        self.file_pattern = self.key.split("|")[0]
        self.filter_aliases = self.key.split("|")[1:]

        exclude_at_root = ['artifacts', 'logs', 'output', 'output-long']
        exclude_everywhere = ['.git']

        for dirpath, filename in self.walk(".", exclude_at_root, exclude_everywhere):
            raw_filepath = os.path.join(dirpath, filename)
            filepath = os.path.normpath(raw_filepath)
            if fnmatch.fnmatch(filepath, self.file_pattern):
                if len(self.filter_aliases) > 0:
                    doc_key = "%s|%s" % (filepath, "|".join(self.filter_aliases))
                else:
                    doc_key = filepath
                self.wrapper.log.debug("Creating doc %s" % doc_key)

                doc_args = self.args.copy()
                doc_args['wrapper'] = self.wrapper

                children = []
                if doc_args.has_key('depends'):
                    if doc_args.get('depends'):
                        children = [a for a in self.wrapper.registered if isinstance(a, Doc)]
                    del doc_args['depends']

                doc = Doc(doc_key, *children, **doc_args)
                self.children.append(doc)

        self.after_setup()
