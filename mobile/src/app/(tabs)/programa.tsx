import * as DocumentPicker from 'expo-document-picker';
import { router } from 'expo-router';
import { useState } from 'react';
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { api } from '../../api';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Button, Card, ConfirmDialog, ErrorText, Header } from '../../ui';

export default function Programa() {
  const [pdf, setPdf] = useState<DocumentPicker.DocumentPickerAsset | null>(null);
  const [confirmPub, setConfirmPub] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const choose = async () => {
    const r = await DocumentPicker.getDocumentAsync({ type: 'application/pdf', copyToCacheDirectory: true });
    if (!r.canceled) { setPdf(r.assets[0]); setError(null); setMsg(null); }
  };

  const publish = async () => {
    if (!pdf) return;
    setConfirmPub(false); setPublishing(true); setError(null); setMsg(null);
    try {
      const form = new FormData();
      // En web el asset trae el File del navegador; en el teléfono se envía por URI.
      if (Platform.OS === 'web' && pdf.file) form.append('file', pdf.file, pdf.name);
      else form.append('file', { uri: pdf.uri, name: pdf.name, type: 'application/pdf' } as any);
      const r = await api('/competitions', { form });
      setMsg(`Programa publicado${r?.status ? ` (${r.status})` : ''}.`);
      setPdf(null);
    } catch (e: any) { setError(e.message); }
    finally { setPublishing(false); }
  };

  return (
    <View style={s.root}>
      <Header title="Cargar programa" subtitle="Calendario y series de un torneo" onBack={() => router.replace('/config')} right={<ProfileButton />} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }} keyboardShouldPersistTaps="handled">
        <Card>
          <Text style={s.h}>PROGRAMA DE CAMPEONATO (PDF)</Text>
          <View style={{ gap: 12, marginTop: 8 }}>
            <Button title={pdf ? pdf.name : 'Elegir PDF'} variant="outline" onPress={choose} disabled={publishing} />
            <Button title="Publicar programa" onPress={() => setConfirmPub(true)} disabled={!pdf || publishing} loading={publishing} />
            {publishing ? <Text style={s.sub}>Subiendo y leyendo el programa… puede tardar hasta un minuto. No cierres la app.</Text> : null}
            <Text style={s.sub}>El nombre del torneo se lee del PDF. Será visible para todos en Torneos; si ya existe uno con el mismo nombre se reemplaza.</Text>
          </View>
        </Card>
        {msg ? <Text style={{ color: c.deep, fontFamily: font.semi }}>{msg}</Text> : null}
        <ErrorText text={error} />
      </ScrollView>
      <ConfirmDialog visible={confirmPub} title="¿Publicar el programa?" confirmLabel="Publicar"
        message={`${pdf?.name ?? ''}. Será visible para todos los usuarios; si ya existe uno con el mismo nombre se reemplaza.`}
        onConfirm={publish} onCancel={() => setConfirmPub(false)} />
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  h: { fontFamily: font.bold, fontSize: 11, letterSpacing: 0.6, color: c.muted },
  sub: { fontFamily: font.body, fontSize: 12, color: c.muted, marginTop: 4 },
});
