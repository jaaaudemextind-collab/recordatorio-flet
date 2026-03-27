import flet as ft
import os
import re
import pytz
import calendar
from datetime import datetime
from supabase import create_client, Client

# --- CONFIGURACIÓN SUPABASE ---
SUPABASE_URL = "https://bywrnjgvcggqvvptnpnv.supabase.co" 
SUPABASE_KEY = "sb_publishable_ptTFX7JnTw7Jcx6F14Xpqg_q_n7MGQ5"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def main(page: ft.Page):
    # --- CONFIGURACIÓN DE VENTANA ---
    page.title = "Jose A.A.A.-LTIND"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0f172a" 
    page.padding = 20
    page.scroll = ft.ScrollMode.ADAPTIVE

    # Estado de la aplicación
    state = {"materias": [], "entregas": [], "completadas": [], "completadas_count": 0, "historial_completadas": {}}
    filtro_activo = {"tipo": "todos", "valor": None}
    tarea_editando = {"ref": None}

    # --- COMPONENTES UI PRINCIPALES ---
    lista_tareas_ui = ft.Column(spacing=12)
    lista_completadas_ui = ft.Column(spacing=8, visible=False)
    dashboard_ui = ft.Row(wrap=True, spacing=10)
    calendario_grid = ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5)
    
    # --- COMPONENTES DE NOTIFICACIÓN (CORREGIDOS) ---
    txt_notif_count = ft.Text("0", size=10, weight="bold", color="white")
    badge_notif = ft.Container(
        content=txt_notif_count,
        bgcolor="#ef4444",
        border_radius=10,
        padding=ft.padding.only(left=5, right=5),
        top=0,
        right=0,
        visible=False
    )
    
    btn_notificaciones = ft.Stack([
        ft.IconButton(
            icon=ft.Icons.NOTIFICATIONS_OUTLINED, 
            icon_color="#94a3b8", 
            on_click=lambda _: mostrar_alerta_vencimiento()
        ),
        badge_notif
    ])

    pb_barra = ft.ProgressBar(height=8, border_radius=5, color="#f59e0b", bgcolor="#1e293b", value=0)
    txt_pct = ft.Text("0% Completado", size=12, weight="bold", color="#f59e0b")
    txt_titulo_lista = ft.Text("Pendientes Críticos", size=16, weight="bold", expand=True)
    txt_contador = ft.Text("0 pendientes", size=12, color="#64748b")

    # --- FUNCIONES DE BASE DE DATOS ---

    def cargar_datos_db():
        try:
            res_m = supabase.table("materias").select("*").execute()
            state["materias"] = [m["nombre"] for m in res_m.data]
            
            res_e = supabase.table("entregas").select("*").eq("completada", False).execute()
            state["entregas"] = res_e.data
            
            res_c = supabase.table("entregas").select("*").eq("completada", True).execute()
            state["completadas"] = res_c.data
            state["completadas_count"] = len(res_c.data)
            
            historial = {}
            for t in res_c.data:
                m = t["materia"]
                historial[m] = historial.get(m, 0) + 1
            state["historial_completadas"] = historial

            dd_materia.options = [ft.dropdown.Option(m) for m in state["materias"]]
            actualizar_progreso()
            renderizar_tareas()
            renderizar_historial()
            renderizar_calendario()
            actualizar_notificaciones() # Mantiene la campana al día
        except Exception as ex:
            print(f"Error de conexión Supabase: {ex}")

    def guardar_y_refrescar():
        cargar_datos_db()

    # --- LÓGICA DE NEGOCIO ---

    def actualizar_notificaciones():
        urgentes = 0
        for t in state["entregas"]:
            _, _, _, segundos = obtener_tiempo_restante(t["fecha"])
            # Si falta menos de 24 horas y no ha vencido
            if 0 < segundos <= 86400:
                urgentes += 1
        
        if urgentes > 0:
            txt_notif_count.value = str(urgentes)
            badge_notif.visible = True
        else:
            badge_notif.visible = False
        page.update()

    def mostrar_alerta_vencimiento():
        page.snack_bar = ft.SnackBar(
            ft.Text(f"Tienes {txt_notif_count.value} entregas prioritarias para hoy."),
            bgcolor="#1e293b",
            action="Entendido"
        )
        page.snack_bar.open = True
        page.update()

    def actualizar_progreso():
        pend = len(state["entregas"])
        comp = state["completadas_count"]
        total = pend + comp
        val = comp / total if total > 0 else 0
        pb_barra.value = val
        txt_pct.value = f"{int(val*100)}% de avance académico"
        page.update()

    def filtrar_por_materia(materia_nombre):
        filtro_activo["tipo"] = "materia"
        filtro_activo["valor"] = materia_nombre
        sb_filtros.selected = {"todos"}
        renderizar_tareas()

    def filtrar_por_dia(dia):
        filtro_activo["tipo"] = "dia"
        filtro_activo["valor"] = dia
        renderizar_tareas()

    def actualizar_dashboard():
        dashboard_ui.controls = []
        for mat_dash, count in state["historial_completadas"].items():
            if count > 0:
                dashboard_ui.controls.append(
                    ft.Container(
                        content=ft.Text(f"{mat_dash}: {count}", size=10, weight="bold", 
                                       color="#f59e0b" if filtro_activo["valor"] == mat_dash else "#94a3b8"),
                        bgcolor="#1e293b", padding=8, border_radius=8, 
                        border=ft.border.all(1, "#f59e0b" if filtro_activo["valor"] == mat_dash else "#334155"),
                        on_click=lambda _, m=mat_dash: filtrar_por_materia(m)
                    )
                )

    def renderizar_calendario():
        mexico_tz = pytz.timezone('America/Mexico_City')
        ahora = datetime.now(mexico_tz)
        mes, anio = ahora.month, ahora.year
        tareas_dias = {}
        for t in state["entregas"]:
            try:
                d = int(t["fecha"].split("/")[0])
                tareas_dias[d] = tareas_dias.get(d, 0) + 1
            except: continue
        cal = calendar.monthcalendar(anio, mes)
        nombres_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        grid_rows = [
            ft.Text(f"{nombres_meses[mes-1]} {anio}", size=14, weight="bold"),
            ft.Row([ft.Text(d, size=10, width=32, text_align="center", color="#64748b") for d in ["L","M","M","J","V","S","D"]], alignment=ft.MainAxisAlignment.CENTER)
        ]
        for week in cal:
            week_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=5)
            for day in week:
                if day == 0:
                    week_row.controls.append(ft.Container(width=32, height=32))
                else:
                    tiene_tarea = day in tareas_dias
                    es_hoy = (day == ahora.day)
                    week_row.controls.append(
                        ft.Container(
                            content=ft.Column([
                                ft.Text(str(day), size=11, weight="bold" if tiene_tarea else "normal", color="white" if not tiene_tarea else "#f59e0b"),
                                ft.Container(width=4, height=4, bgcolor="#f59e0b", border_radius=2, visible=tiene_tarea)
                            ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                            width=32, height=35,
                            bgcolor="#3b82f6" if es_hoy else "#1e293b",
                            border_radius=6,
                            on_click=lambda _, d=day: filtrar_por_dia(d)
                        )
                    )
            grid_rows.append(week_row)
        calendario_grid.controls = grid_rows
        page.update()

    def obtener_tiempo_restante(fecha_str):
        try:
            mexico_tz = pytz.timezone('America/Mexico_City')
            ahora = datetime.now(mexico_tz)
            fecha_meta = datetime.strptime(f"{fecha_str} {ahora.year}", "%d/%m %H:%M %Y")
            fecha_meta = mexico_tz.localize(fecha_meta)
            diff = fecha_meta - ahora
            segundos = diff.total_seconds()
            if segundos < 0: return "⚠️ Vencida", "#ef4444", False, segundos
            urgente = segundos < 86400 
            dias, horas = diff.days, diff.seconds // 3600
            mins = (diff.seconds % 3600) // 60
            if dias > 0: return f"Faltan {dias}d {horas}h", "#94a3b8", urgente, segundos
            if horas > 0: return f"En {horas}h {mins}m", "#fbbf24", urgente, segundos
            return f"En {mins} min", "#f59e0b", urgente, segundos
        except: return "Pendiente", "#64748b", False, 999999

    def completar_tarea(entrega):
        supabase.table("entregas").update({"completada": True}).eq("id", entrega["id"]).execute()
        guardar_y_refrescar()

    def recuperar_tarea(entrega):
        supabase.table("entregas").update({"completada": False}).eq("id", entrega["id"]).execute()
        guardar_y_refrescar()

    def iniciar_edicion(entrega):
        tarea_editando["ref"] = entrega
        dd_materia.value = entrega["materia"]; dd_prio.value = entrega["prio"]
        txt_act.value = entrega["actividad"]; txt_fec.value = entrega["fecha"]
        btn_registrar.text = "Actualizar"; btn_registrar.bgcolor = ft.Colors.BLUE_700
        btn_registrar.icon = ft.Icons.EDIT_NOTE; page.update()

    def crear_card_tarea(entrega):
        prio_conf = {"Crítica": "#ef4444", "Media": "#f59e0b", "Baja": "#3b82f6"}
        conf_color = prio_conf.get(entrega.get("prio", "Media"), "#f59e0b")
        txt_tiempo, color_tiempo, _, _ = obtener_tiempo_restante(entrega['fecha'])
        return ft.Container(
            content=ft.Row([
                ft.Container(width=5, bgcolor=conf_color, border_radius=5, height=60),
                ft.Row([
                    ft.Column([
                        ft.Text(entrega['materia'], weight="bold", size=14),
                        ft.Text(entrega['actividad'], size=13, color="#94a3b8"),
                        ft.Row([ft.Text(f"📅 {entrega['fecha']}", size=11, color="#f8fafc"), ft.Text(txt_tiempo, size=11, weight="bold", color=color_tiempo)], spacing=10)
                    ], spacing=2, expand=True),
                    ft.Row([
                        ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_size=18, icon_color="#94a3b8", on_click=lambda _: iniciar_edicion(entrega)),
                        ft.IconButton(icon=ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED, icon_color="#10b981", on_click=lambda _: completar_tarea(entrega))
                    ], spacing=0)
                ], expand=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#1e293b", border_radius=12, border=ft.border.all(1, "#334155"), padding=12
        )

    def renderizar_tareas():
        tareas_a_mostrar = state["entregas"]
        hay_urgente = False
        if filtro_activo["tipo"] == "proximas":
            txt_titulo_lista.value = "Próximas (48h)"
            tareas_a_mostrar = [t for t in state["entregas"] if 0 <= obtener_tiempo_restante(t["fecha"])[3] <= 172800]
        elif filtro_activo["tipo"] == "materia":
            txt_titulo_lista.value = f"Materia: {filtro_activo['valor']}"
            tareas_a_mostrar = [t for t in state["entregas"] if t["materia"] == filtro_activo["valor"]]
        elif filtro_activo["tipo"] == "dia":
            txt_titulo_lista.value = f"Entregas del día {filtro_activo['valor']}"
            tareas_a_mostrar = [t for t in state["entregas"] if int(t["fecha"].split("/")[0]) == filtro_activo["valor"]]
        else:
            txt_titulo_lista.value = "Pendientes Críticos"

        for t in tareas_a_mostrar:
            if 0 <= obtener_tiempo_restante(t["fecha"])[3] <= 86400: hay_urgente = True; break
        txt_contador.value = f"{len(tareas_a_mostrar)} pendientes"
        txt_contador.color = "#ef4444" if hay_urgente else "#64748b"
        pesos = {"Crítica": 0, "Media": 1, "Baja": 2}
        ordenadas = sorted(tareas_a_mostrar, key=lambda x: pesos.get(x.get("prio", "Media"), 1))
        lista_tareas_ui.controls = [crear_card_tarea(ent) for ent in ordenadas]
        if not tareas_a_mostrar: lista_tareas_ui.controls = [ft.Container(ft.Text("Sin tareas", italic=True, color="#64748b"), padding=20)]
        actualizar_dashboard()
        page.update()

    def renderizar_historial():
        lista_completadas_ui.controls = [ft.Container(content=ft.Row([ft.Column([ft.Text(f"{c['materia']}: {c['actividad']}", size=12, color="#94a3b8", italic=True)], expand=True), ft.TextButton("Deshacer", icon=ft.Icons.UNDO, on_click=lambda _, item=c: recuperar_tarea(item))]), padding=5, border=ft.border.only(bottom=ft.border.BorderSide(1, "#1e293b"))) for c in reversed(state["completadas"])]
        if not state["completadas"]: lista_completadas_ui.controls = [ft.Text("Vacío", size=12, color="#64748b")]
        page.update()

    # --- UI COMPONENTS ---
    sb_filtros = ft.SegmentedButton(selected={"todos"}, on_change=lambda e: (setattr(filtro_activo, "tipo", list(e.control.selected)[0]), renderizar_tareas()), segments=[ft.Segment(value="todos", label=ft.Text("Todo"), icon=ft.Icon(ft.Icons.ALL_INCLUSIVE)), ft.Segment(value="proximas", label=ft.Text("Próximo"), icon=ft.Icon(ft.Icons.TIMER_OUTLINED))])
    txt_nueva_mat = ft.TextField(label="Nueva Materia", expand=True, border_radius=10)
    dd_materia = ft.Dropdown(label="Asignatura", expand=True, border_radius=10, text_size=12)
    btn_filtro_rapido = ft.IconButton(icon=ft.Icons.FILTER_ALT_OUTLINED, icon_color="#3b82f6", on_click=lambda _: filtrar_por_materia(dd_materia.value))
    dd_prio = ft.Dropdown(label="Prioridad", width=110, border_radius=10, options=[ft.dropdown.Option(x) for x in ["Crítica", "Media", "Baja"]], value="Media")
    txt_act = ft.TextField(label="Descripción", border_radius=10)
    txt_fec = ft.TextField(label="Fecha (DD/MM HH:MM)", border_radius=10, expand=True)

    def registrar(e):
        if not re.match(r"^\d{2}/\d{2} \d{2}:\d{2}$", txt_fec.value): txt_fec.error_text = "Error formato"; page.update(); return
        nueva_data = {"materia": dd_materia.value, "actividad": txt_act.value, "fecha": txt_fec.value, "prio": dd_prio.value}
        if tarea_editando["ref"]:
            supabase.table("entregas").update(nueva_data).eq("id", tarea_editando["ref"]["id"]).execute()
            tarea_editando["ref"] = None
            btn_registrar.text = "Guardar"; btn_registrar.bgcolor = "#f59e0b"
        else: supabase.table("entregas").insert(nueva_data).execute()
        txt_act.value = ""; txt_fec.value = ""; guardar_y_refrescar()

    btn_registrar = ft.FloatingActionButton(icon=ft.Icons.PLAYLIST_ADD_ROUNDED, bgcolor="#f59e0b", on_click=registrar, text="Guardar")
    btn_historial = ft.TextButton("Ver historial de completadas", icon=ft.Icons.KEYBOARD_ARROW_DOWN, on_click=lambda _: (setattr(lista_completadas_ui, "visible", not lista_completadas_ui.visible), page.update()))

    # --- ENSAMBLADO ---
    page.add(
        ft.Row([
            ft.CircleAvatar(content=ft.Text("JA"), bgcolor="#f59e0b", color="black"), 
            ft.Column([ft.Text("Jose A Alcantara Aladin", size=18, weight="bold"), ft.Text("LTIND UDEMEX", size=12, color="#94a3b8")], spacing=0, expand=True), 
            btn_notificaciones, 
            ft.IconButton(ft.Icons.SETTINGS_SUGGEST_ROUNDED, on_click=lambda _: None)
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Column([txt_pct, pb_barra], spacing=5),
        ft.Text("Dashboard de Logros", size=11, weight="bold", color="#64748b"),
        dashboard_ui,
        ft.Divider(height=10, color="transparent"),
        ft.Text("Calendario de Entregas", size=11, weight="bold", color="#64748b"),
        ft.Container(calendario_grid, padding=15, bgcolor="#1e293b", border_radius=15),
        ft.Divider(height=10, color="transparent"),
        ft.Row([sb_filtros], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row([txt_nueva_mat, ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color="#f59e0b", on_click=lambda _: (supabase.table("materias").insert({"nombre": txt_nueva_mat.value}).execute(), setattr(txt_nueva_mat, "value", ""), guardar_y_refrescar()))]),
        ft.Row([dd_materia, btn_filtro_rapido, dd_prio]),
        txt_act,
        ft.Row([txt_fec, btn_registrar]),
        ft.Divider(height=20, color="#334155"),
        ft.Row([txt_titulo_lista, txt_contador]),
        lista_tareas_ui,
        btn_historial,
        lista_completadas_ui
    )
    cargar_datos_db()

if __name__ == "__main__":
    ft.app(target=main)