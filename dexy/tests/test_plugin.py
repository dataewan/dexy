import dexy.plugin

def test_plugin_meta():
    new_class = dexy.plugin.PluginMeta(
            "Foo",
            (dexy.plugin.Plugin,),
            {
                'aliases' : [],
                "__doc__" : 'help',
                '__metaclass__' : dexy.plugin.PluginMeta
                }
            )

    assert new_class.__name__ == 'Foo'
    assert new_class.__doc__ == 'help'
    assert new_class.aliases == []
    assert new_class.plugins == {}

class WidgetBase(dexy.plugin.Plugin):
    __metaclass__ = dexy.plugin.PluginMeta
    _settings = {
            'foo' : ("Default value for foo", "bar"),
            'abc' : ("Default value for abc", 123)
            }

class Widget(WidgetBase):
    aliases = ['widget']

class SubWidget(Widget):
    aliases = ['sub']
    _settings = {
            'foo' : 'baz'
            }

def test_create_instance():
    widget = Widget.create_instance('widget')
    assert widget.setting('foo') == 'bar'

    sub = Widget.create_instance('sub')
    assert sub.setting('foo') == 'baz'
    assert sub.setting('abc') == 123
    assert sub.setting_values()['foo'] == 'baz'
    assert sub.setting_values()['abc'] == 123

class Fruit(dexy.plugin.Plugin):
    __metaclass__ = dexy.plugin.PluginMeta
    aliases = ['fruit']
    _settings = {}

class Starch(dexy.plugin.Plugin):
    __metaclass__ = dexy.plugin.PluginMeta
    aliases = ['starch']
    _settings = {}
    _other_class_settings = {
            'fruit' : {
                    "color" : ("The color of the fruit", "red")
                }
            }

def test_other_class_settings():
    fruit = Fruit()
    fruit.initialize_settings()
    assert fruit.setting('color') == 'red'
