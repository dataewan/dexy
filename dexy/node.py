from dexy.utils import md5_hash
from dexy.utils import os_to_posix
import dexy.doc
import dexy.plugin
import fnmatch
import re
import json

class Node(dexy.plugin.Plugin):
    """
    base class for Nodes
    """
    aliases = ['node']
    __metaclass__ = dexy.plugin.PluginMeta
    _settings = {}
    state_transitions = (
            ('new', 'cached'),
            ('new', 'checked'),
            ('checked', 'running'),
            ('running', 'ran'),
            )

    def __init__(self, pattern, wrapper, inputs=None, **kwargs):
        self.key = os_to_posix(pattern)
        self.wrapper = wrapper
        self.args = kwargs
        if inputs:
            self.inputs = list(inputs)
        else:
            self.inputs = []

        self.initialize_settings(**kwargs)

        self.start_time = 0
        self.finish_time = 0
        self.elapsed_time = 0

        self.runtime_args = {}
        self.children = []
        self.additional_docs = []

        self.hashid = md5_hash(self.key)

        self.state = 'new'
        self.args_changed = self.check_args_changed()
        self.doc_changed = None

        # Class-specific setup.
        self.setup()

        assert_msg = "custom setup method for %s must set doc_changed"
        assert self.doc_changed is not None, assert_msg % self.key_with_class()

    def setup(self):
        self.doc_changed = self.check_doc_changed()
   
    def check_doc_changed(self):
        return False

    def __repr__(self):
        return "%s(%s)" % ( self.__class__.__name__, self.key)

    def transition(self, new_state):
        attempted_transition = (self.state, new_state) 
        if not attempted_transition in self.__class__.state_transitions:
            msg = "%s -> %s"
            raise dexy.exceptions.UnexpectedState(msg % attempted_transition)
        self.state = new_state

    def add_runtime_args(self, args):
        self.args.update(args)
        self.runtime_args.update(args)

    def arg_value(self, key, default=None):
        return self.args.get(key, default) or self.args.get(key.replace("-", "_"), default)

    def walk_inputs(self):
        """
        Yield all direct inputs and their inputs.
        """
        children = []
        def walk(inputs):
            for inpt in inputs:
                children.append(inpt)
                walk(inpt.inputs + inpt.children)

        if self.inputs:
            walk(self.inputs)
        elif hasattr(self, 'parent'):
            children = self.parent.walk_inputs()

        return children

    def walk_input_docs(self):
        """
        Yield all direct inputs and their inputs, if they are of class 'doc'
        """
        for node in self.walk_inputs():
            if node.__class__.__name__ == 'Doc':
                yield node

    def log_debug(self, message):
        self.wrapper.log.debug("%s %s: %s" % (self.hashid, self.key_with_class(), message))

    def log_info(self, message):
        self.wrapper.log.info("%s %s: %s" % (self.hashid, self.key_with_class(), message))

    def log_warn(self, message):
        self.wrapper.log.warn("%s %s: %s" % (self.hashid, self.key_with_class(), message))

    def key_with_class(self):
        return "%s:%s" % (self.__class__.aliases[0], self.key)

    def check_args_changed(self):
        """
        Checks if args have changed by comparing calculated hash against the
        archived calculated hash from last run.
        """
        saved_args = self.wrapper.saved_args.get(self.key_with_class())
        if not saved_args:
            self.log_debug("no saved args, will return True for args_changed")
            return True
        else:
            self.log_debug("saved args '%s' (%s)" % (saved_args, saved_args.__class__))
            self.log_debug("sorted args '%s' (%s)" % (self.sorted_arg_string(), self.sorted_arg_string().__class__))
            self.log_debug("unequal: %s" % (saved_args != self.sorted_arg_string()))
            return saved_args != self.sorted_arg_string()

    def sorted_args(self, skip=['contents']):
        """
        Returns a list of args in sorted order.
        """
        if not skip:
            skip = []

        sorted_args = []
        for k in sorted(self.args):
            if not k in skip:
                sorted_args.append((k, self.args[k]))
        return sorted_args

    def sorted_arg_string(self):
        """
        Returns a string representation of args in sorted order.
        """
        return unicode(json.dumps(self.sorted_args()))

    def additional_doc_info(self):
        additional_doc_info = []
        for doc in self.additional_docs:
            info = (doc.key, doc.hashid, doc.setting_values())
            additional_doc_info.append(info)
        return additional_doc_info

    def load_additional_docs(self, additional_doc_info):
        for doc_key, hashid, doc_settings in additional_doc_info:
            new_doc = dexy.doc.Doc(doc_key,
                    self.wrapper,
                    [],
                    contents='dummy contents',
                    **doc_settings
                    )
            new_doc.contents = None
            new_doc.args_changed = False
            assert new_doc.hashid == hashid
            new_doc.calculate_is_cached()
            new_doc.initial_data.load_data()
            new_doc.output_data().load_data()
            self.add_additional_doc(new_doc)

    def add_additional_doc(self, doc):
        self.log_debug("adding additional doc '%s'" % doc.key)
        doc.created_by_doc = self
        self.children.append(doc)
        self.wrapper.add_node(doc)
        self.wrapper.batch.add_doc(doc)
        self.additional_docs.append(doc)

    def calculate_is_cached(self):
        if self.state == 'new':
            self.log_debug("checking if %s is changed" % self.key)

            any_inputs_not_cached = False
            input_nodes = self.inputs + self.children

            if hasattr(self, 'parent'):
                input_nodes.extend(self.parent.inputs)

            for node in input_nodes:
                node.calculate_is_cached()
                if not node.state == 'cached':
                    self.log_debug("input node %s is not cached" % node.key_with_class())
                    any_inputs_not_cached = True
                
            self.log_debug("  doc changed %s" % self.doc_changed)
            self.log_debug("  args changed %s" % self.args_changed)
            self.log_debug("  any inputs not cached %s" % any_inputs_not_cached)
            is_cached = not self.doc_changed and not self.args_changed and not any_inputs_not_cached

            if is_cached:
                self.transition('cached')

                # Do once-off stuff for cached tasks.
                self.wrapper.batch.add_doc(self)

                runtime_info = self.wrapper.prev_batch_runtime_info.get(self.key_with_class())
                if runtime_info:
                    self.add_runtime_args(runtime_info['runtime-args'])
                    self.load_additional_docs(runtime_info['additional-docs'])
            else:
                self.transition('checked')

    def __iter__(self):
        def next_task():
            if self.state in ('checked'):
                self.transition('running')
                yield self
                self.transition('ran')

            elif self.state == 'running':
                raise dexy.exceptions.CircularDependency(self.key)

            elif self.state in ('ran', 'cached'):
                pass # do nothing

            else:
                raise dexy.exceptions.UnexpectedState("%s in %s" % (self.state, self.key))

        return next_task()

    def __call__(self, *args, **kw):
        for inpt in self.inputs:
            for task in inpt:
                task()

        self.run()

    def run(self):
        """
        Method which processes node's content if not cached, also responsible
        for calling child nodes.
        """
        for child in self.children:
            for task in child:
                task()

class BundleNode(Node):
    """
    Node representing a bundle of other nodes.
    """
    aliases = ['bundle']

class ScriptNode(BundleNode):
    """
    Node representing a bundle of other nodes which must always run in a set
    order, so if any of the bundle siblings change, the whole bundle should be
    re-run.
    """
    aliases = ['script']

    def check_doc_changed(self):
        return any(i.doc_changed for i in self.inputs)

    def setup(self):
        self.script_storage = {}

        siblings = []
        for doc in self.inputs:
            doc.inputs = doc.inputs + siblings
            siblings.append(doc)

        self.doc_changed = self.check_doc_changed()

        for doc in self.inputs:
            if not self.doc_changed:
                assert not doc.doc_changed
            doc.doc_changed = self.doc_changed

class PatternNode(Node):
    """
    A node which takes a file matching pattern and creates individual Doc
    objects for all files that match the pattern.
    """
    aliases = ['pattern']

    def check_doc_changed(self):
        return any(child.doc_changed for child in self.children)

    def setup(self):
        file_pattern = self.key.split("|")[0]
        filter_aliases = self.key.split("|")[1:]

        for filepath, fileinfo in self.wrapper.filemap.iteritems():
            if fnmatch.fnmatch(filepath, file_pattern):
                except_p = self.args.get('except')
                if except_p and re.search(except_p, filepath):
                    msg = "not creating child of patterndoc for file '%s' because it matches except '%s'"
                    msgargs = (filepath, except_p)
                    self.log_debug(msg % msgargs)
                else:
                    if len(filter_aliases) > 0:
                        doc_key = "%s|%s" % (filepath, "|".join(filter_aliases))
                    else:
                        doc_key = filepath

                    msg = "creating child of patterndoc %s: %s"
                    msgargs = (self.key, doc_key)
                    self.log_debug(msg % msgargs)
                    doc = dexy.doc.Doc(doc_key, self.wrapper, [], **self.args)
                    doc.parent = self
                    self.children.append(doc)
                    self.wrapper.add_node(doc)
                    self.wrapper.batch.add_doc(doc)

        self.doc_changed = self.check_doc_changed()
