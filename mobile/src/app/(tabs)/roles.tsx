import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, Item } from '../../api';
import { useAuth } from '../../auth';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Button, Card, Chip, ConfirmDialog, Empty, ErrorText, Field, Header } from '../../ui';

type Section = 'usuarios' | 'roles' | 'permisos';
type Dialog =
  | { kind: 'userRole'; u: Item; role: string }
  | { kind: 'role'; role: Item | null; id: string; name: string; perms: string[] }
  | { kind: 'perm'; perm: Item | null; key: string; label: string }
  | { kind: 'delRole'; role: Item }
  | { kind: 'delPerm'; perm: Item };

const slug = (t: string) =>
  t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 30);

export default function Roles() {
  const { user } = useAuth();
  const [section, setSection] = useState<Section>('usuarios');
  const [roles, setRoles] = useState<Item[]>([]);
  const [perms, setPerms] = useState<Item[]>([]);
  const [users, setUsers] = useState<Item[]>([]);
  const [q, setQ] = useState('');
  const [dialog, setDialog] = useState<Dialog | null>(null);
  const [idTouched, setIdTouched] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dialogError, setDialogError] = useState<string | null>(null);

  const loadCatalog = useCallback(async () => {
    try {
      const r = await api('/admin/roles');
      setRoles(r.roles); setPerms(r.permissions);
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  const loadUsers = useCallback(async (term: string) => {
    try { setUsers((await api(`/admin/users?q=${encodeURIComponent(term.trim())}`)).items); }
    catch (e: any) { setError(e.message); }
  }, []);

  useEffect(() => { loadCatalog(); }, [loadCatalog]);
  useEffect(() => {
    const t = setTimeout(() => loadUsers(q), 300);
    return () => clearTimeout(t);
  }, [q, loadUsers]);

  const close = () => { setDialog(null); setDialogError(null); setIdTouched(false); };

  // Ejecuta una llamada, recarga y cierra; los errores se muestran dentro del cuadro.
  const run = async (fn: () => Promise<unknown>, done: string) => {
    setBusy(true); setDialogError(null); setError(null); setMsg(null);
    try {
      await fn();
      await Promise.all([loadCatalog(), loadUsers(q)]);
      setMsg(done);
      close();
    } catch (e: any) { setDialogError(e.message); }
    finally { setBusy(false); }
  };

  const confirm = () => {
    if (!dialog) return;
    if (dialog.kind === 'userRole') {
      return run(() => api(`/admin/users/${dialog.u.id}/role`, { method: 'PUT', body: { role: dialog.role } }),
        `${dialog.u.email} ahora tiene el rol ${roles.find((r) => r.id === dialog.role)?.name ?? dialog.role}. Aplica de inmediato.`);
    }
    if (dialog.kind === 'role') {
      const body = { id: dialog.id, name: dialog.name, permissions: dialog.perms };
      return dialog.role
        ? run(() => api(`/admin/roles/${dialog.role!.id}`, { method: 'PUT', body }), 'Rol actualizado. Aplica de inmediato.')
        : run(() => api('/admin/roles', { method: 'POST', body }), 'Rol creado.');
    }
    if (dialog.kind === 'perm') {
      return dialog.perm
        ? run(() => api(`/admin/permissions/${dialog.perm!.key}`, { method: 'PUT', body: { label: dialog.label } }), 'Permiso actualizado.')
        : run(() => api('/admin/permissions', { method: 'POST', body: { key: dialog.key, label: dialog.label } }), 'Permiso creado. El rol Administrador lo recibe automáticamente.');
    }
    if (dialog.kind === 'delRole') return run(() => api(`/admin/roles/${dialog.role.id}`, { method: 'DELETE' }), 'Rol eliminado.');
    if (dialog.kind === 'delPerm') return run(() => api(`/admin/permissions/${dialog.perm.key}`, { method: 'DELETE' }), 'Permiso eliminado.');
  };

  const permLabel = (key: string) => perms.find((p) => p.key === key)?.label ?? key;
  const toggle = (key: string) => {
    if (dialog?.kind !== 'role') return;
    setDialog({ ...dialog, perms: dialog.perms.includes(key) ? dialog.perms.filter((k) => k !== key) : [...dialog.perms, key] });
  };

  const dlg = (() => {
    if (!dialog) return null;
    switch (dialog.kind) {
      case 'userRole': return {
        title: 'Cambiar rol', message: dialog.u.email, confirmLabel: 'Guardar', danger: false,
        disabled: dialog.role === dialog.u.role,
        body: (
          <View style={{ marginTop: 10, gap: 6 }}>
            {roles.map((r) => (
              <Pressable key={r.id} onPress={() => setDialog({ ...dialog, role: r.id })} accessibilityRole="radio" accessibilityState={{ selected: dialog.role === r.id }}
                style={[s.opt, dialog.role === r.id && { borderColor: c.primary, borderWidth: 1.5 }]}>
                <Text style={s.optName}>{r.name}</Text>
                <Text style={s.sub}>{r.permissions.length} permisos</Text>
              </Pressable>
            ))}
          </View>
        ),
      };
      case 'role': {
        const isNew = !dialog.role;
        return {
          title: isNew ? 'Nuevo rol' : 'Editar rol', message: isNew ? 'Elige un nombre y qué puede hacer.' : `Identificador: ${dialog.role!.id}`,
          confirmLabel: 'Guardar', danger: false, disabled: !dialog.name.trim() || (isNew && dialog.id.length < 2),
          body: (
            <View>
              <Field label="Nombre" value={dialog.name} placeholder="Entrenador" maxLength={60}
                onChangeText={(t) => setDialog({ ...dialog, name: t, id: isNew && !idTouched ? slug(t) : dialog.id })} />
              {isNew ? <Field label="Identificador (minúsculas, números y _)" value={dialog.id} autoCapitalize="none" maxLength={31}
                onChangeText={(t) => { setIdTouched(true); setDialog({ ...dialog, id: slug(t) }); }} /> : null}
              <Text style={[s.sub, { marginTop: 14, marginBottom: 6 }]}>Permisos</Text>
              <ScrollView style={{ maxHeight: 230 }} nestedScrollEnabled>
                {perms.map((p) => {
                  const on = dialog.perms.includes(p.key);
                  return (
                    <Pressable key={p.key} onPress={() => toggle(p.key)} accessibilityRole="checkbox" accessibilityState={{ checked: on }} style={s.permRow}>
                      <View style={[s.box, on && { backgroundColor: c.primary, borderColor: c.primary }]}>{on ? <Text style={s.tick}>✓</Text> : null}</View>
                      <Text style={[s.optName, { flex: 1 }]}>{p.label}</Text>
                    </Pressable>
                  );
                })}
              </ScrollView>
              {!isNew && !dialog.role!.is_system ? (
                <Pressable onPress={() => setDialog({ kind: 'delRole', role: dialog.role! })} style={{ marginTop: 12 }}><Text style={s.danger}>Eliminar este rol</Text></Pressable>
              ) : null}
            </View>
          ),
        };
      }
      case 'perm': {
        const isNew = !dialog.perm;
        return {
          title: isNew ? 'Nuevo permiso' : 'Editar permiso',
          message: isNew ? 'Los permisos propios sirven para funciones futuras: hoy no abren nada por sí solos.' : `Clave: ${dialog.perm!.key}`,
          confirmLabel: 'Guardar', danger: false, disabled: !dialog.label.trim() || (isNew && dialog.key.length < 2),
          body: (
            <View>
              <Field label="Etiqueta" value={dialog.label} placeholder="Ver marcas mínimas" maxLength={60}
                onChangeText={(t) => setDialog({ ...dialog, label: t, key: isNew && !idTouched ? slug(t) : dialog.key })} />
              {isNew ? <Field label="Clave (minúsculas, números y _)" value={dialog.key} autoCapitalize="none" maxLength={31}
                onChangeText={(t) => { setIdTouched(true); setDialog({ ...dialog, key: slug(t) }); }} /> : null}
              {!isNew && !dialog.perm!.is_system ? (
                <Pressable onPress={() => setDialog({ kind: 'delPerm', perm: dialog.perm! })} style={{ marginTop: 12 }}><Text style={s.danger}>Eliminar este permiso</Text></Pressable>
              ) : null}
            </View>
          ),
        };
      }
      case 'delRole': return {
        title: '¿Eliminar este rol?', message: `${dialog.role.name}. Dejará de existir; no se puede deshacer.`, confirmLabel: 'Eliminar', danger: true, disabled: false, body: null,
      };
      case 'delPerm': return {
        title: '¿Eliminar este permiso?', message: `${dialog.perm.label}. Se le quitará a los ${dialog.perm.roles} rol(es) que lo tienen; no se puede deshacer.`, confirmLabel: 'Eliminar', danger: true, disabled: false, body: null,
      };
    }
  })();

  return (
    <View style={s.root}>
      <Header title="Roles y permisos" subtitle="Quién puede hacer qué en la app" right={<ProfileButton />} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }} keyboardShouldPersistTaps="handled">
        <View style={{ flexDirection: 'row', gap: 8, flexShrink: 0 }}>
          <Chip label="Usuarios" selected={section === 'usuarios'} onPress={() => setSection('usuarios')} />
          <Chip label="Roles" selected={section === 'roles'} onPress={() => setSection('roles')} />
          <Chip label="Permisos" selected={section === 'permisos'} onPress={() => setSection('permisos')} />
        </View>
        {msg ? <Text style={{ color: c.deep, fontFamily: font.semi }}>{msg}</Text> : null}
        <ErrorText text={error} />
        {loading ? <ActivityIndicator color={c.primary} style={{ marginTop: 16 }} /> : null}

        {section === 'usuarios' ? (
          <>
            <TextInput value={q} onChangeText={setQ} placeholder="Buscar por correo" placeholderTextColor="#8AA3B5" autoCapitalize="none" style={s.search} />
            {users.length === 0 && !loading ? <Empty text="Sin usuarios para esa búsqueda." /> : null}
            {users.map((u) => {
              const self = u.email === user?.email;
              return (
                <Card key={u.id}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                    <View style={{ flex: 1 }}>
                      <Text style={s.optName} numberOfLines={1}>{u.email}{self ? ' (tú)' : ''}</Text>
                      <Text style={s.sub}>{u.role_name}</Text>
                    </View>
                    {!self ? (
                      <Pressable onPress={() => setDialog({ kind: 'userRole', u, role: u.role })} accessibilityRole="button" style={s.smallBtn}>
                        <Text style={s.smallBtnText}>Cambiar rol</Text>
                      </Pressable>
                    ) : null}
                  </View>
                </Card>
              );
            })}
          </>
        ) : null}

        {section === 'roles' ? (
          <>
            <Button title="Nuevo rol" onPress={() => { setIdTouched(false); setDialog({ kind: 'role', role: null, id: '', name: '', perms: [] }); }} />
            {roles.map((r) => (
              <Card key={r.id}>
                <Text style={s.optName}>{r.name} <Text style={s.sub}>· {r.id}{r.is_system ? ' · sistema' : ''}</Text></Text>
                <Text style={s.sub}>{r.users} usuario(s) · {r.permissions.length} permiso(s)</Text>
                <Text style={[s.sub, { color: c.text }]}>{r.permissions.map(permLabel).join(' · ') || 'Sin permisos'}</Text>
                {r.id === 'admin' ? (
                  <Text style={[s.sub, { marginTop: 8 }]}>Siempre tiene todos los permisos; no se edita ni se elimina.</Text>
                ) : (
                  <Pressable onPress={() => setDialog({ kind: 'role', role: r, id: r.id, name: r.name, perms: r.permissions })} accessibilityRole="button" style={[s.smallBtn, { alignSelf: 'flex-start', marginTop: 10 }]}>
                    <Text style={s.smallBtnText}>Editar</Text>
                  </Pressable>
                )}
              </Card>
            ))}
          </>
        ) : null}

        {section === 'permisos' ? (
          <>
            <Button title="Nuevo permiso" onPress={() => { setIdTouched(false); setDialog({ kind: 'perm', perm: null, key: '', label: '' }); }} />
            {perms.map((p) => (
              <Card key={p.key}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                  <View style={{ flex: 1 }}>
                    <Text style={s.optName}>{p.label}</Text>
                    <Text style={s.sub}>{p.key} · {p.is_system ? 'sistema' : 'propio'} · en {p.roles} rol(es)</Text>
                  </View>
                  <Pressable onPress={() => setDialog({ kind: 'perm', perm: p, key: p.key, label: p.label })} accessibilityRole="button" style={s.smallBtn}>
                    <Text style={s.smallBtnText}>Editar</Text>
                  </Pressable>
                </View>
              </Card>
            ))}
            <Text style={s.sub}>Los permisos «de sistema» los usa el código de la app: puedes cambiarles la etiqueta pero no eliminarlos.</Text>
          </>
        ) : null}
      </ScrollView>

      {dlg ? (
        <ConfirmDialog visible title={dlg.title} message={dlg.message} confirmLabel={busy ? 'Guardando…' : dlg.confirmLabel}
          danger={dlg.danger} confirmDisabled={busy || dlg.disabled} onConfirm={confirm} onCancel={close}>
          {dlg.body}
          <ErrorText text={dialogError} />
        </ConfirmDialog>
      ) : null}
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  sub: { fontFamily: font.body, fontSize: 12, color: c.muted, marginTop: 2 },
  search: { height: 48, minHeight: 48, borderWidth: 1, borderColor: c.input, borderRadius: 14, paddingHorizontal: 14, backgroundColor: c.white, fontFamily: font.body, fontSize: 14, color: c.text, flexShrink: 0 },
  optName: { fontFamily: font.semi, fontSize: 14, color: c.text },
  opt: { borderWidth: 1, borderColor: c.border, borderRadius: 12, padding: 12, backgroundColor: c.white },
  permRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 9 },
  box: { width: 22, height: 22, borderRadius: 6, borderWidth: 1.5, borderColor: c.input, alignItems: 'center', justifyContent: 'center', backgroundColor: c.white },
  tick: { color: c.white, fontFamily: font.bold, fontSize: 14, lineHeight: 16 },
  smallBtn: { borderWidth: 1, borderColor: c.primary, borderRadius: 10, paddingVertical: 6, paddingHorizontal: 12 },
  smallBtnText: { color: c.primary, fontFamily: font.semi, fontSize: 12 },
  danger: { color: c.danger, fontFamily: font.semi, fontSize: 13 },
});
