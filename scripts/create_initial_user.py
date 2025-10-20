"""Utility script to create an initial user in the database."""

from __future__ import annotations

import argparse
from getpass import getpass

from sqlalchemy.exc import SQLAlchemyError

from app.application.use_cases.users.create_user import create_user
from app.infrastructure.database import SessionLocal, initialize_database


def parse_args() -> argparse.Namespace:
    """Parse command line arguments for user creation."""

    parser = argparse.ArgumentParser(
        description="Create an initial user for the Accura API application.",
    )
    parser.add_argument(
        "--name",
        default="Administrador",
        help="Nombre completo del usuario (por defecto: Administrador)",
    )
    parser.add_argument(
        "--email",
        default="admin@example.com",
        help="Correo electrónico del usuario (por defecto: admin@example.com)",
    )
    parser.add_argument(
        "--alias",
        default=None,
        help="Alias u apodo del usuario (opcional)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Contraseña del usuario. Si no se proporciona se solicitará interactivamente.",
    )
    parser.add_argument(
        "--must-change-password",
        action="store_true",
        help="Indica si el usuario debe cambiar la contraseña en el primer ingreso.",
    )
    return parser.parse_args()


def main() -> None:
    """Create a user using the provided command line arguments."""

    args = parse_args()

    password = args.password or getpass("Ingrese la contraseña del usuario: ")
    if not password:
        raise SystemExit("No se proporcionó una contraseña válida.")

    initialize_database()

    session = SessionLocal()
    try:
        user = create_user(
            session,
            name=args.name,
            email=args.email,
            password=password,
            alias=args.alias,
            must_change_password=args.must_change_password,
        )
    except ValueError as exc:
        session.rollback()
        raise SystemExit(f"No se pudo crear el usuario: {exc}") from exc
    except SQLAlchemyError as exc:
        session.rollback()
        raise SystemExit(f"Error al guardar el usuario en la base de datos: {exc}") from exc
    else:
        print(
            "Usuario creado exitosamente:\n"
            f"  ID: {user.id}\n"
            f"  Nombre: {user.name}\n"
            f"  Email: {user.email}\n"
            f"  Alias: {user.alias or '-'}"
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()
