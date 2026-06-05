import flet as ft
import sqlite3
import os
from datetime import datetime
import webbrowser

# === CONFIGURACIÓN DE LA BASE DE DATOS LOCAL ===
DB_NAME = "data_gestor.db"

def inicializar_bd():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabla de Usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            clave TEXT
        )
    ''')
    # Tabla de Contraseñas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credenciales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            sitio_nombre TEXT,
            tipo TEXT,
            link TEXT,
            password TEXT,
            ultima_modificacion TEXT,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
        )
    ''')
    conn.commit()
    conn.close()

# Inicializamos la base de datos de inmediato
inicializar_bd()

class GestorApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "🔐 Mis Contraseñas Offline"
        self.page.window_width = 450
        self.page.window_height = 700
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.horizontal_alignment = "center"
        self.page.vertical_alignment = "center"
        
        # Estado de la sesión
        self.usuario_actual_id = None
        self.usuario_actual_nombre = ""
        self.credencial_a_editar_id = None  

        # Inicializar pantallas
        self.mostrar_login()

    # ================= PANTALLAS PRINCIPALES =================
    
    def mostrar_login(self):
        self.page.clean()
        
        txt_user = ft.TextField(label="Usuario", prefix_icon=ft.Icons.PERSON, width=300)
        txt_pass = ft.TextField(label="Contraseña", prefix_icon=ft.Icons.LOCK, password=True, can_reveal_password=True, width=300)
        lbl_error = ft.Text("", color="red400")

        def intentar_login(e):
            if not txt_user.value or not txt_pass.value:
                lbl_error.value = "Completa todos los campos"
                self.page.update()
                return
            
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT id, usuario FROM usuarios WHERE usuario = ? AND clave = ?", (txt_user.value.strip(), txt_pass.value))
            resultado = cursor.fetchone()
            conn.close()

            if resultado:
                self.usuario_actual_id = resultado[0]
                self.usuario_actual_nombre = resultado[1]
                self.mostrar_boveda()
            else:
                lbl_error.value = "Usuario o contraseña incorrectos"
                self.page.update()

        self.page.add(
            ft.Column(
                controls=[
                    ft.Icon(ft.Icons.LOCK_PERSON_ROUNDED, size=80, color="blueAccent"),
                    ft.Text("GESTIONAR CLAVES", size=26, weight=ft.FontWeight.BOLD),
                    ft.Text("Acceso seguro y local", color="grey400"),
                    ft.Container(height=10),
                    txt_user,
                    txt_pass,
                    lbl_error,
                    ft.Container(height=10),
                    ft.FilledButton(content=ft.Text("Iniciar Sesión", weight=ft.FontWeight.BOLD), width=300, on_click=intentar_login),
                    ft.TextButton(content=ft.Text("¿No tienes cuenta? Regístrate aquí"), on_click=lambda _: self.mostrar_registro())
                ],
                horizontal_alignment="center",
                spacing=12
            )
        )
        self.page.update()

    def mostrar_registro(self):
        self.page.clean()
        
        txt_user = ft.TextField(label="Nuevo Usuario", prefix_icon=ft.Icons.PERSON_ADD, width=300)
        txt_pass = ft.TextField(label="Contraseña Segura", prefix_icon=ft.Icons.LOCK, password=True, can_reveal_password=True, width=300)
        lbl_status = ft.Text("", color="red400")

        def registrar_usuario(e):
            user = txt_user.value.strip()
            password = txt_pass.value
            if not user or not password:
                lbl_status.value = "Por favor, llena los campos"
                self.page.update()
                return
            
            try:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO usuarios (usuario, clave) VALUES (?, ?)", (user, password))
                conn.commit()
                conn.close()
                self.mostrar_login()
            except sqlite3.IntegrityError:
                lbl_status.value = "Ese nombre de usuario ya existe"
                self.page.update()

        self.page.add(
            ft.Column(
                controls=[
                    ft.Icon(ft.Icons.APP_REGISTRATION_ROUNDED, size=70, color="greenAccent"),
                    ft.Text("REGISTRO DE USUARIO", size=24, weight=ft.FontWeight.BOLD),
                    ft.Container(height=10),
                    txt_user,
                    txt_pass,
                    lbl_status,
                    ft.Container(height=10),
                    ft.FilledButton(
                        content=ft.Text("Crear Cuenta", color="black", weight=ft.FontWeight.BOLD), 
                        width=300, 
                        style=ft.ButtonStyle(bgcolor="greenAccent"), 
                        on_click=registrar_usuario
                    ),
                    ft.TextButton(content=ft.Text("Volver al Login"), on_click=lambda _: self.mostrar_login())
                ],
                horizontal_alignment="center",
                spacing=12
            )
        )
        self.page.update()

    def mostrar_boveda(self):
        self.page.clean()
        
        self.lista_claves = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=15)
        self.cargar_credenciales_usuario()

        self.page.add(
            ft.Row(
                [
                    ft.Text(f"👤 {self.usuario_actual_nombre}", size=16, weight=ft.FontWeight.BOLD, color="blue200"),
                    ft.IconButton(ft.Icons.LOGOUT_ROUNDED, icon_color="red300", on_click=lambda _: self.cerrar_sesion())
                ],
                alignment="spaceBetween"
            ),
            ft.Divider(),
            ft.Text("Tus Contraseñas Guardadas", size=18, weight=ft.FontWeight.W_500),
            ft.Container(content=self.lista_claves, expand=True, padding=10),
            ft.FloatingActionButton(
                bgcolor="blueAccent", 
                content=ft.Row([ft.Icon(ft.Icons.ADD, color="white"), ft.Text(" Añadir ", color="white", weight=ft.FontWeight.BOLD)], alignment="center", spacing=5),
                on_click=lambda _: self.abrir_formulario_modal()
            )
        )
        self.page.update()

    # ================= LÓGICA DE NEGOCIO / BD =================

    def cargar_credenciales_usuario(self):
        self.lista_claves.controls.clear()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, sitio_nombre, tipo, link, password, ultima_modificacion FROM credenciales WHERE usuario_id = ? ORDER BY sitio_nombre ASC",
            (self.usuario_actual_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            self.lista_claves.controls.append(
                ft.Container(
                    content=ft.Text("No tienes contraseñas registradas aún.", color="grey500", text_align="center"),
                    margin=20, 
                    alignment="center"
                )
            )
            return

        for row in rows:
            c_id, nombre, tipo, link, clave, ultima_mod = row
            
            if tipo == "Web" and link:
                url = link if link.startswith(("http://", "https://")) else f"https://{link}"
                componente_titulo = ft.TextButton(
                    content=ft.Text(f"🌐 {nombre}", color="lightBlue200", size=16, weight=ft.FontWeight.BOLD),
                    style=ft.ButtonStyle(padding=0),
                    on_click=lambda e, u=url: webbrowser.open(u)
                )
            else:
                componente_titulo = ft.Text(f"📱 {nombre}", size=18, weight=ft.FontWeight.BOLD, color="white")

            # SOLUCIÓN COMPATIBLE: Usamos padding tradicional numérico directo, 
            # soportado de forma idéntica por cualquier versión clásica y moderna.
            etiqueta_tipo = ft.Container(
                content=ft.Text(tipo, size=11, color="white", weight=ft.FontWeight.BOLD),
                bgcolor="blueGrey700",
                padding=5,  # Valor numérico directo compatible con versiones viejas y nuevas
                border_radius=5
            )

            # Corregidos los IconButtons para usar icon_size y evitar el error 'size'
            tarjeta = ft.Container(
                bgcolor="surfaceVariant",
                padding=15,
                border_radius=10,
                content=ft.Column(
                    [
                        ft.Row([componente_titulo, etiqueta_tipo], alignment="spaceBetween"),
                        ft.Row(
                            [
                                ft.Text(f"Clave: {clave}", size=15, color="green200", selectable=True),
                                ft.Row([
                                    ft.IconButton(ft.Icons.EDIT, icon_color="amber300", icon_size=20, on_click=lambda e, idx=c_id: self.abrir_formulario_modal(idx)),
                                    ft.IconButton(ft.Icons.DELETE, icon_color="red400", icon_size=20, on_click=lambda e, idx=c_id: self.eliminar_credencial(idx))
                                ])
                            ],
                            alignment="spaceBetween"
                        ),
                        ft.Text(f"Última edición: {ultima_mod}", size=11, color="grey400", italic=True)
                    ],
                    spacing=5
                )
            )
            self.lista_claves.controls.append(tarjeta)

    def abrir_formulario_modal(self, credencial_id=None):
        self.credencial_a_editar_id = credencial_id
        
        txt_nombre = ft.TextField(label="Nombre del Sitio / App", width=300)
        radio_tipo = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="Web", label="Página Web"),
                ft.Radio(value="App", label="Aplicación Móvil")
            ], alignment="center")
        )
        
        txt_link = ft.TextField(label="Enlace (URL)", hint_text="ejemplo.com", width=300, visible=False)
        txt_password = ft.TextField(label="Contraseña", password=True, can_reveal_password=True, width=300)

        def al_cambiar_tipo(e):
            txt_link.visible = (radio_tipo.value == "Web")
            self.page.update()

        radio_tipo.on_change = al_cambiar_tipo

        if credencial_id:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT sitio_nombre, tipo, link, password FROM credenciales WHERE id = ?", (credencial_id,))
            datos = cursor.fetchone()
            conn.close()
            if datos:
                txt_nombre.value, radio_tipo.value, txt_link.value, txt_password.value = datos
                if radio_tipo.value == "Web": txt_link.visible = True

        def guardar_datos(e):
            if not txt_nombre.value or not radio_tipo.value or not txt_password.value:
                return 
            
            link_final = txt_link.value.strip() if radio_tipo.value == "Web" else ""
            fecha_ahora = datetime.now().strftime("%d/%m/%Y %I:%M %p")

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            if self.credencial_a_editar_id:
                cursor.execute(
                    '''UPDATE credenciales SET sitio_nombre=?, tipo=?, link=?, password=?, ultima_modificacion=? WHERE id=?''',
                    (txt_nombre.value.strip(), radio_tipo.value, link_final, txt_password.value, fecha_ahora, self.credencial_a_editar_id)
                )
            else:
                cursor.execute(
                    '''INSERT INTO credenciales (usuario_id, sitio_nombre, tipo, link, password, ultima_modificacion) VALUES (?, ?, ?, ?, ?, ?)''',
                    (self.usuario_actual_id, txt_nombre.value.strip(), radio_tipo.value, link_final, txt_password.value, fecha_ahora)
                )
            
            conn.commit()
            conn.close()
            
            dialogo_modal.open = False
            self.mostrar_boveda()

        dialogo_modal = ft.AlertDialog(
            title=ft.Text("Guardar Credencial", text_align="center"),
            content=ft.Column(
                [txt_nombre, ft.Text("Tipo de registro:"), radio_tipo, txt_link, txt_password],
                tight=True, spacing=10
            ),
            actions=[
                ft.TextButton(content=ft.Text("Cancelar"), on_click=lambda _: setattr(dialogo_modal, 'open', False) or self.page.update()),
                ft.FilledButton(content=ft.Text("Guardar", color="white", weight=ft.FontWeight.BOLD), style=ft.ButtonStyle(bgcolor="blueAccent"), on_click=guardar_datos)
            ],
            actions_alignment="end"
        )

        self.page.overlay.append(dialogo_modal)
        dialogo_modal.open = True
        self.page.update()

    def eliminar_credencial(self, credencial_id):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM credenciales WHERE id = ?", (credencial_id,))
        conn.commit()
        conn.close()
        self.mostrar_boveda()

    def cerrar_sesion(self):
        self.usuario_actual_id = None
        self.usuario_actual_nombre = ""
        self.mostrar_login()


def main(page: ft.Page):
    GestorApp(page)

if __name__ == "__main__":
    ft.run(main)