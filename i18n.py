"""Offline UI translations. No network calls or runtime machine translation."""
LANGUAGES = {
    "en": "English", "de": "Deutsch", "es": "Español", "fr": "Français",
    "pt": "Português", "it": "Italiano", "ja": "日本語", "zh": "简体中文",
}
# Columns: key | English | German | Spanish | French | Portuguese | Italian | Japanese | Simplified Chinese
_ROWS = r'''
settings|Settings|Einstellungen|Ajustes|Paramètres|Configurações|Impostazioni|設定|设置
support|Support on Ko-fi (opens your browser)|Auf Ko-fi unterstützen (öffnet den Browser)|Apoyar en Ko-fi (abre el navegador)|Soutenir sur Ko-fi (ouvre le navigateur)|Apoiar no Ko-fi (abre o navegador)|Sostieni su Ko-fi (apre il browser)|Ko-fiで応援（ブラウザーが開きます）|在 Ko-fi 上支持（打开浏览器）
language|Language|Sprache|Idioma|Langue|Idioma|Lingua|言語|语言
weekly_used|Weekly quota used|Wochenlimit verbraucht|Cuota semanal usada|Quota hebdo utilisé|Cota semanal usada|Quota settimanale usata|週間枠の使用率|每周额度已用
demo|Demo|Demo|Demo|Démo|Demo|Demo|デモ|演示
thresholds|Alert at usage (%)|Warnen ab Verbrauch (%)|Avisar al consumir (%)|Alerter à partir de (%)|Alertar ao atingir (%)|Avvisa al consumo (%)|通知する使用率 (%)|通知阈值 (%)
corner|Screen corner|Bildschirmecke|Esquina de pantalla|Coin de l’écran|Canto da tela|Angolo dello schermo|表示位置|屏幕角落
bottom-right|Bottom right|Unten rechts|Abajo a la derecha|En bas à droite|Inferior direito|In basso a destra|右下|右下角
bottom-left|Bottom left|Unten links|Abajo a la izquierda|En bas à gauche|Inferior esquerdo|In basso a sinistra|左下|左下角
top-right|Top right|Oben rechts|Arriba a la derecha|En haut à droite|Superior direito|In alto a destra|右上|右上角
top-left|Top left|Oben links|Arriba a la izquierda|En haut à gauche|Superior esquerdo|In alto a sinistra|左上|左上角
monitor|Monitor|Monitor|Monitor|Écran|Monitor|Monitor|モニター|显示器
visible_for|Visible for|Sichtbar für|Duración|Durée d’affichage|Duração|Durata|表示時間|显示时长
seconds|seconds|Sekunden|segundos|secondes|segundos|secondi|秒|秒
minutes|minutes|Minuten|minutos|minutes|minutos|minuti|分|分钟
poll_every|Check usage every|Verbrauch abfragen alle|Consultar consumo cada|Vérifier l’utilisation toutes les|Consultar uso a cada|Controlla il consumo ogni|使用率の確認間隔|用量检查间隔
animation|Animation|Animation|Animación|Animation|Animação|Animazione|アニメーション|动画
slide|Gentle slide in and out|Sanftes Gleiten|Deslizamiento suave|Glissement doux|Deslizamento suave|Scorrimento delicato|滑らかに出入りする|柔和滑入滑出
save|Save|Speichern|Guardar|Enregistrer|Salvar|Salva|保存|保存
cancel|Cancel|Abbrechen|Cancelar|Annuler|Cancelar|Annulla|キャンセル|取消
ok|OK|OK|Aceptar|OK|OK|OK|OK|确定
bad_thresholds|Enter comma-separated whole numbers from 1 to 100.|Kommagetrennte ganze Zahlen von 1 bis 100 eingeben.|Introduce enteros del 1 al 100 separados por comas.|Saisissez des entiers de 1 à 100 séparés par des virgules.|Digite números inteiros de 1 a 100 separados por vírgulas.|Inserisci numeri interi da 1 a 100 separati da virgole.|1〜100の整数を半角カンマで区切って入力してください。|请输入 1 到 100 的整数，用英文逗号分隔。
bad_settings|Invalid settings; defaults loaded.|Einstellungen ungültig; Standardwerte geladen.|Ajustes no válidos; se cargaron los valores predeterminados.|Paramètres invalides ; valeurs par défaut chargées.|Configurações inválidas; padrões carregados.|Impostazioni non valide; caricati i valori predefiniti.|設定が無効なため、初期設定を使用しています。|设置无效，已加载默认值。
demo_mode|Demo mode|Demo-Modus|Modo demo|Mode démo|Modo demo|Modalità demo|デモモード|演示模式
checking|Checking usage…|Verbrauch wird abgefragt …|Consultando consumo…|Vérification de l’utilisation…|Consultando uso…|Controllo del consumo…|使用率を確認中…|正在检查用量…
no_data|No live data yet|Noch keine Live-Daten|Aún no hay datos reales|Pas encore de données réelles|Ainda sem dados reais|Nessun dato reale disponibile|まだ実データがありません|暂无实时数据
show_current|Show current usage|Aktuellen Stand anzeigen|Mostrar consumo actual|Afficher l’utilisation actuelle|Mostrar uso atual|Mostra il consumo attuale|現在の使用率を表示|显示当前用量
test_popup|Test popup · {value} %|Test-Popup · {value} %|Probar aviso · {value} %|Tester l’alerte · {value} %|Testar aviso · {value} %|Prova avviso · {value} %|通知テスト · {value} %|测试弹窗 · {value} %
pause|Pause notifications|Hinweise pausieren|Pausar notificaciones|Suspendre les notifications|Pausar notificações|Sospendi le notifiche|通知を一時停止|暂停通知
quit|Quit|Beenden|Salir|Quitter|Sair|Esci|終了|退出
unavailable|Usage unavailable|Abfrage nicht verfügbar|Consumo no disponible|Utilisation indisponible|Uso indisponível|Consumo non disponibile|使用率を取得できません|无法获取用量
usage_status|{value} % of weekly quota used|{value} % des Wochenlimits verbraucht|{value} % de la cuota semanal usada|{value} % du quota hebdomadaire utilisé|{value} % da cota semanal usada|{value} % della quota settimanale usata|週間枠を {value} % 使用|每周额度已用 {value} %
reset_at|Resets: {date}|Reset: {date}|Se restablece: {date}|Réinitialisation : {date}|Renova em: {date}|Ripristino: {date}|リセット: {date}|重置时间：{date}
state_error|Unable to save notification history|Warnstatus kann nicht gespeichert werden|No se puede guardar el historial de avisos|Impossible d’enregistrer l’historique des alertes|Não foi possível salvar o histórico de avisos|Impossibile salvare la cronologia degli avvisi|通知履歴を保存できません|无法保存通知记录
save_error|Unable to save settings.|Einstellungen konnten nicht gespeichert werden.|No se pudieron guardar los ajustes.|Impossible d’enregistrer les paramètres.|Não foi possível salvar as configurações.|Impossibile salvare le impostazioni.|設定を保存できません。|无法保存设置。
already_running|Already running. Find the icon in the system tray beside the clock.|Läuft bereits. Das Symbol ist im Infobereich neben der Uhr.|Ya está en ejecución. Busca el icono en la bandeja del sistema junto al reloj.|Déjà lancé. Retrouvez l’icône dans la zone de notification près de l’horloge.|Já está em execução. Procure o ícone na bandeja do sistema ao lado do relógio.|È già in esecuzione. Cerca l’icona nell’area di notifica accanto all’orologio.|すでに起動しています。時計の横の通知領域にアイコンがあります。|程序已在运行，请查看时钟旁的系统托盘图标。
no_tray|No system tray is available.|Kein Infobereich verfügbar.|La bandeja del sistema no está disponible.|Aucune zone de notification disponible.|A bandeja do sistema não está disponível.|Area di notifica non disponibile.|通知領域を利用できません。|系统托盘不可用。
no_bucket|No general Work/Codex quota is available.|Kein allgemeines Work-/Codex-Kontingent verfügbar.|No hay una cuota general de Work/Codex disponible.|Aucun quota général Work/Codex disponible.|Nenhuma cota geral do Work/Codex disponível.|Nessuna quota generale Work/Codex disponibile.|Work/Codexの共通枠を取得できません。|无法获取 Work/Codex 通用额度。
no_week|No unambiguous weekly quota was returned. No estimate shown.|Kein eindeutiges Wochenlimit geliefert; keine Schätzung.|No se recibió una cuota semanal inequívoca. No se muestra una estimación.|Aucun quota hebdomadaire non ambigu reçu. Aucune estimation affichée.|Nenhuma cota semanal inequívoca recebida. Nenhuma estimativa exibida.|Nessuna quota settimanale univoca ricevuta. Nessuna stima mostrata.|週間枠を特定できません。推定値は表示しません。|未返回明确的每周额度，不显示估算值。
invalid_usage|Invalid usage value.|Ungültiger Verbrauchswert.|Valor de consumo no válido.|Valeur d’utilisation invalide.|Valor de uso inválido.|Valore di consumo non valido.|使用率の値が無効です。|用量值无效。
stale_data|Reset time is missing or usage data has expired.|Reset-Zeit fehlt oder Verbrauchsdaten sind veraltet.|Falta la hora de restablecimiento o los datos han caducado.|Heure de réinitialisation absente ou données périmées.|Horário de renovação ausente ou dados desatualizados.|Ora di ripristino mancante o dati scaduti.|リセット時刻がないか、使用率データが古くなっています。|缺少重置时间或用量数据已过期。
missing_cli|Install the Windows Codex CLI and sign in with ChatGPT.|Windows-Codex-CLI installieren und mit ChatGPT anmelden.|Instala Codex CLI para Windows e inicia sesión con ChatGPT.|Installez Codex CLI pour Windows et connectez-vous avec ChatGPT.|Instale a Codex CLI para Windows e entre com o ChatGPT.|Installa Codex CLI per Windows e accedi con ChatGPT.|Windows版Codex CLIをインストールし、ChatGPTでログインしてください。|请安装 Windows 版 Codex CLI 并使用 ChatGPT 登录。
missing_entry|Codex entry point not found. Use a native or npm CLI installation.|Codex-Startdatei fehlt. Native CLI oder npm-Installation verwenden.|No se encontró el inicio de Codex. Usa la CLI nativa o instalada con npm.|Point d’entrée Codex introuvable. Utilisez la CLI native ou installée via npm.|Arquivo de inicialização do Codex ausente. Use a CLI nativa ou via npm.|Avvio di Codex non trovato. Usa la CLI nativa o installata tramite npm.|Codexの起動ファイルがありません。ネイティブ版またはnpm版CLIを使用してください。|找不到 Codex 启动文件，请使用原生版或 npm 安装的 CLI。
cancelled|Request cancelled.|Abfrage beendet.|Consulta cancelada.|Requête annulée.|Consulta cancelada.|Richiesta annullata.|リクエストを中止しました。|请求已取消。
timeout|Codex usage request timed out.|Zeitlimit der Codex-Abfrage überschritten.|La consulta a Codex agotó el tiempo de espera.|Délai de la requête Codex dépassé.|A consulta ao Codex excedeu o tempo limite.|La richiesta a Codex è scaduta.|Codexへの問い合わせがタイムアウトしました。|Codex 用量请求超时。
disconnected|Codex connection closed.|Codex-Verbindung beendet.|Conexión con Codex cerrada.|Connexion Codex fermée.|Conexão com o Codex encerrada.|Connessione a Codex chiusa.|Codexとの接続が終了しました。|Codex 连接已关闭。
rpc_error|Codex rejected the request. Check your sign-in and CLI version.|Codex meldet einen Fehler. Anmeldung und CLI-Version prüfen.|Codex rechazó la consulta. Revisa la sesión y la versión de la CLI.|Codex a refusé la requête. Vérifiez la connexion et la version de la CLI.|O Codex recusou a consulta. Verifique o login e a versão da CLI.|Codex ha rifiutato la richiesta. Controlla l’accesso e la versione della CLI.|Codexがリクエストを拒否しました。ログイン状態とCLIのバージョンを確認してください。|Codex 拒绝了请求，请检查登录状态和 CLI 版本。
sign_in|Sign in to Codex CLI with the same ChatGPT account, not an API key.|Codex CLI mit demselben ChatGPT-Konto anmelden, nicht per API-Key.|Inicia sesión en Codex CLI con la misma cuenta de ChatGPT, no con una clave API.|Connectez Codex CLI au même compte ChatGPT, sans clé API.|Entre na Codex CLI com a mesma conta do ChatGPT, não com chave de API.|Accedi a Codex CLI con lo stesso account ChatGPT, senza chiave API.|同じChatGPTアカウントでCodex CLIにログインしてください。APIキーは使用しません。|请使用同一个 ChatGPT 账号登录 Codex CLI，而不是 API 密钥。
connection_failed|Connection failed. Check Codex CLI and your internet connection.|Verbindung fehlgeschlagen. Codex CLI und Internetverbindung prüfen.|Conexión fallida. Revisa Codex CLI y la conexión a Internet.|Échec de connexion. Vérifiez Codex CLI et votre connexion Internet.|Falha na conexão. Verifique a Codex CLI e a conexão à Internet.|Connessione non riuscita. Controlla Codex CLI e la connessione Internet.|接続に失敗しました。Codex CLIとインターネット接続を確認してください。|连接失败，请检查 Codex CLI 和网络连接。
'''
CATALOGS = {code: {} for code in LANGUAGES}
for _row in _ROWS.strip().splitlines():
    _key, *_values = _row.split('|')
    if len(_values) != len(LANGUAGES):
        raise ValueError(f"Translation column count: {_key}")
    for _code, _value in zip(LANGUAGES, _values):
        CATALOGS[_code][_key] = _value


def tr(language, key, **values):
    """Unknown languages and missing keys fall back to English."""
    template = CATALOGS.get(language, CATALOGS['en']).get(key, CATALOGS['en'].get(key, key))
    return template.format(**values)
