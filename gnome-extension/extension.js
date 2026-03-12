import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';

const IFACE = `
<node>
  <interface name="com.geforcenow.WindowTitles">
    <method name="GetGFNTitle">
      <arg type="s" direction="out" name="title"/>
    </method>
  </interface>
</node>`;

export default class WindowTitleServerExtension extends Extension {
    _dbusId = null;

    enable() {
        this._dbusId = Gio.DBus.session.register_object(
            '/com/geforcenow/WindowTitles',
            Gio.DBusNodeInfo.new_for_xml(IFACE).interfaces[0],
            (connection, sender, path, ifaceName, methodName, params, invocation) => {
                if (methodName === 'GetGFNTitle') {
                        const gfnWindows = global.get_window_actors()
                            .map(a => a.meta_window)
                            .filter(w => {
                                const cls = (w.get_wm_class() || '').toLowerCase();
                                return cls.includes('geforce') || cls.includes('geforcenow');
                            });
                    const title = gfnWindows.length > 0 ? (gfnWindows[0].get_title() || '') : '';
                    invocation.return_value(new GLib.Variant('(s)', [title]));
                }
            },
            null,
            null
        );
    }

    disable() {
        if (this._dbusId) {
            Gio.DBus.session.unregister_object(this._dbusId);
            this._dbusId = null;
        }
    }
}
