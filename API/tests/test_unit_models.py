"""Tests unitaires — modèles ORM SQLAlchemy (models/)."""

import pytest
from models.user import User
from models.trajet import Trajet

pytestmark = pytest.mark.unit


def test_user_table_and_columns():
    assert User.__tablename__ == "users"
    cols = User.__table__.columns
    assert "id" in cols
    assert "username" in cols
    assert cols["username"].unique is True
    assert cols["username"].nullable is False


def test_user_role_default_is_user(db_session):
    user = User(username="charlie", password="hash")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    assert user.role == "user"


def test_trajet_composite_primary_key():
    pk_cols = [c.name for c in Trajet.__table__.primary_key.columns]
    # 7 colonnes composent la clé primaire du trajet
    assert "year" in pk_cols
    assert "origin_station_name" in pk_cols
    assert "destination_station_name" in pk_cols
    assert len(pk_cols) == 7


def test_trajet_mapped_column_names():
    # Les attributs Python sont mappés vers des noms de colonnes explicites en base.
    # __table__.columns est indexé par le nom de colonne réel.
    column_names = {c.name for c in Trajet.__table__.columns}
    assert "Passengers_millions" in column_names
    assert "Type" in column_names

    # L'attribut Python `passengers_millions` pointe bien vers la colonne "Passengers_millions"
    assert Trajet.passengers_millions.property.columns[0].name == "Passengers_millions"
    assert Trajet.type.property.columns[0].name == "Type"
