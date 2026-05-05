import json
import unittest
import uuid
from pathlib import Path

from backend.database.db import Database
from backend.models.errors import ApiError
from backend.services.auth_service import decode_token, login, register
from backend.services.card_service import draw_cards, draw_special_cards, get_catalog, get_user_inventory
from backend.services.game_service import move
from backend.services.map_service import get_map
from backend.services.progression_service import get_progression, serialize_progression, update_progression
from backend.services.session_service import activate_task, accept_carpooler, apply_session_special_card, choose_starting_trajets, complete_task, create_session, finish_turn, join_session, leave_session, list_sessions, move_in_session, player_interaction, start_session, use_city_service
from backend.services.skin_service import fuse_skin, list_skins, lootbox_count, open_lootbox


class BackendServiceTests(unittest.TestCase):
    def setUp(self):
        tmp_root = Path(__file__).resolve().parent / ".tmp"
        tmp_root.mkdir(exist_ok=True)
        self.db_path = tmp_root / f"test-{uuid.uuid4().hex}.sqlite"
        self.db = Database(self.db_path)
        self.db.init()

    def tearDown(self):
        for suffix in ("", "-journal", "-wal", "-shm"):
            path = Path(f"{self.db_path}{suffix}")
            if path.exists():
                path.unlink()

    def set_die(self, conn, session_id, user_id, value=6):
        conn.execute(
            "UPDATE session_players SET dice_remaining = ?, turn_roll = ? WHERE session_id = ? AND user_id = ?",
            (value, value, session_id, user_id),
        )

    def choose_initial_trajets(self, conn, started_session, user_id):
        choices = started_session["starting_trajet_choices"]
        return choose_starting_trajets(
            conn,
            user_id,
            started_session["code"],
            [card["inventory_id"] for card in choices[:3]],
        )

    def add_session_card(self, conn, user_id, session_id, slug, quantity=1):
        card = conn.execute("SELECT id FROM cards WHERE slug = ?", (slug,)).fetchone()
        cursor = conn.execute(
            "INSERT INTO inventory (user_id, session_id, item_type, item_id, quantity, status) VALUES (?, ?, 'card', ?, ?, 'active')",
            (user_id, session_id, card["id"], quantity),
        )
        return cursor.lastrowid

    def test_seeded_catalog_and_map(self):
        with self.db.session() as conn:
            game_map = get_map(conn)
            catalog = get_catalog(conn)
            road_profiles = {
                row["road_type"]: dict(row)
                for row in conn.execute(
                    "SELECT road_type, MAX(cost_coins) AS max_cost, AVG(fuel_cost) AS avg_fuel FROM roads GROUP BY road_type"
                ).fetchall()
            }

        self.assertGreaterEqual(len(game_map["nodes"]), 25)
        self.assertGreaterEqual(len(game_map["roads"]), 30)
        self.assertGreater(game_map["width"], 2000)
        self.assertIn("OMS", {node["id"] for node in game_map["nodes"]})
        self.assertIn("CLF", {node["id"] for node in game_map["nodes"]})
        self.assertEqual(len(game_map["board_routes"]), len(game_map["roads"]))
        paris_route_types = {
            route["road_type"]
            for route in game_map["board_routes"]
            if route["from_node_id"] == "PAR" or route["to_node_id"] == "PAR"
        }
        self.assertTrue({"autoroute", "nationale", "departementale"}.issubset(paris_route_types))
        requested_links = [
            {"KYI", "VOR"},
            {"VOR", "SAM"},
            {"ROS", "UFA"},
            {"RIG", "GOT"},
        ]
        route_links = [
            {route["from_node_id"], route["to_node_id"]}
            for route in game_map["board_routes"]
        ]
        for link in requested_links:
            self.assertIn(link, route_links)
        paris_lyon = [
            route for route in game_map["board_routes"]
            if {route["from_node_id"], route["to_node_id"]} == {"PAR", "LYO"}
        ]
        self.assertEqual(len(paris_lyon), 1)
        self.assertIn(5, {route["case_count"] for route in paris_lyon})
        self.assertGreaterEqual(len([card for card in catalog["cards"] if card["type"] == "trajet"]), 10)
        special_slugs = {card["slug"] for card in catalog["cards"] if card["type"] in ("bonus", "malus")}
        self.assertIn("crevaison", special_slugs)
        self.assertIn("essence-contaminee", special_slugs)
        self.assertNotIn("bouchon", special_slugs)
        self.assertGreaterEqual(len(catalog["skins"]), 35)
        skin_names = {skin["name"] for skin in catalog["skins"]}
        self.assertIn("Twingo Bleu Mediterranee", skin_names)
        self.assertIn("Twingo Dragon", skin_names)
        self.assertTrue(all(skin["asset"].startswith("data:image/svg+xml") for skin in catalog["skins"]))
        self.assertGreater(road_profiles["autoroute"]["max_cost"], 0)
        self.assertEqual(road_profiles["nationale"]["max_cost"], 0)
        self.assertEqual(road_profiles["departementale"]["max_cost"], 0)
        self.assertLess(road_profiles["autoroute"]["avg_fuel"], road_profiles["departementale"]["avg_fuel"])
        self.assertTrue(all("durability" in card["effect"] for card in catalog["cards"] if card["type"] in ("bonus", "malus")))

    def test_register_login_and_token(self):
        with self.db.session() as conn:
            result = register(conn, "pilot@example.com", "secret123", "Pilot")
            payload = decode_token(result["token"])
            logged = login(conn, "pilot@example.com", "secret123")

        self.assertEqual(payload["email"], "pilot@example.com")
        self.assertEqual(logged["user"]["display_name"], "Pilot")
        self.assertEqual(logged["progression"]["current_node_id"], "PAR")
        self.assertEqual(logged["progression"]["fuel"], 35)
        self.assertEqual(logged["progression"]["coins"], 0)
        self.assertIn("twingo-bleu-mediterranee", logged["progression"]["unlocked_skins"])

    def test_move_updates_progression(self):
        with self.db.session() as conn:
            result = register(conn, "move@example.com", "secret123", "Move")
            user_id = result["user"]["id"]
            moved = move(conn, user_id, "LIL")

        self.assertEqual(moved["progression"]["current_node_id"], "LIL")
        self.assertGreaterEqual(moved["progression"]["distance_km"], 225)
        self.assertLess(moved["progression"]["fuel"], 35)

    def test_draw_cards_adds_inventory(self):
        with self.db.session() as conn:
            result = register(conn, "cards@example.com", "secret123", "Cards")
            drawn = draw_cards(conn, result["user"]["id"], 3)

        self.assertEqual(len(drawn["drawn"]), 3)
        self.assertGreaterEqual(len(drawn["inventory"]), 3)

    def test_level_grants_lootbox_and_opening_can_duplicate_skins(self):
        with self.db.session() as conn:
            result = register(conn, "lootbox@example.com", "secret123", "Loot")
            user_id = result["user"]["id"]
            before = lootbox_count(conn, user_id)
            opened = open_lootbox(conn, user_id)
            after = lootbox_count(conn, user_id)
            owned = [skin for skin in opened["skins"] if skin["owned_count"] > 0]

        self.assertEqual(before, 1)
        self.assertEqual(after, 0)
        self.assertGreaterEqual(len(owned), 1)
        self.assertIn(opened["skin"]["rarity"], {"Commun", "Peu commun", "Rare", "Epique", "Legendaire", "Mythique"})

    def test_account_level_uses_distance_thresholds(self):
        with self.db.session() as conn:
            result = register(conn, "distancelevel@example.com", "secret123", "Km")
            user_id = result["user"]["id"]
            update_progression(conn, user_id, xp=5000, distance_km=999)
            level_one = serialize_progression(get_progression(conn, user_id))
            update_progression(conn, user_id, distance_km=1000)
            level_two = serialize_progression(get_progression(conn, user_id))
            update_progression(conn, user_id, distance_km=2500)
            level_three = serialize_progression(get_progression(conn, user_id))
            update_progression(conn, user_id, distance_km=5000)
            level_four = serialize_progression(get_progression(conn, user_id))

        self.assertEqual(level_one["level"], 1)
        self.assertEqual(level_two["level"], 2)
        self.assertEqual(level_three["level"], 3)
        self.assertEqual(level_four["level"], 4)
        self.assertEqual(level_three["next_level_distance_km"], 5000)

    def test_fusing_five_skin_copies_grants_next_rarity(self):
        with self.db.session() as conn:
            result = register(conn, "fuse@example.com", "secret123", "Fuse")
            user_id = result["user"]["id"]
            skin = conn.execute("SELECT id FROM skins WHERE slug = 'twingo-jaune-indien'").fetchone()
            for _ in range(5):
                conn.execute(
                    "INSERT INTO inventory (user_id, item_type, item_id, status) VALUES (?, 'skin', ?, 'unlocked')",
                    (user_id, skin["id"]),
                )
            fused = fuse_skin(conn, user_id, "twingo-jaune-indien")
            source = next(skin for skin in fused["skins"] if skin["slug"] == "twingo-jaune-indien")

        self.assertEqual(fused["skin"]["rarity"], "Peu commun")
        self.assertEqual(source["owned_count"], 0)

    def test_create_and_join_session_sets_turn_order(self):
        with self.db.session() as conn:
            first = register(conn, "first@example.com", "secret123", "First")
            second = register(conn, "second@example.com", "secret123", "Second")
            session = create_session(conn, first["user"]["id"], "Road test")
            joined = join_session(conn, second["user"]["id"], session["code"])

        self.assertEqual(len(joined["players"]), 2)
        self.assertEqual(joined["code"], session["code"])
        self.assertEqual(session["current_turn_user_id"], first["user"]["id"])

    def test_public_sessions_are_visible_to_other_players(self):
        with self.db.session() as conn:
            host = register(conn, "publichost@example.com", "secret123", "Host")
            guest = register(conn, "publicguest@example.com", "secret123", "Guest")
            private_session = create_session(conn, host["user"]["id"], "Private room", visibility="private")
            public_session = create_session(conn, host["user"]["id"], "Public room", visibility="public")
            visible = list_sessions(conn, guest["user"]["id"])
            joined = join_session(conn, guest["user"]["id"], public_session["code"])

        visible_codes = {session["code"] for session in visible}
        public_row = next(session for session in visible if session["code"] == public_session["code"])
        self.assertIn(public_session["code"], visible_codes)
        self.assertNotIn(private_session["code"], visible_codes)
        self.assertFalse(public_row["is_member"])
        self.assertTrue(joined["is_member"])

    def test_tour_europe_mode_uses_country_goal(self):
        visited = ["PAR", "LON", "BRU", "AMS", "BER", "MAD", "LIS", "ROM", "VIE", "PRG", "WAR", "CPH"]
        with self.db.session() as conn:
            result = register(conn, "tourmode@example.com", "secret123", "Tour")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "Tour mode", game_mode="tour_europe")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            conn.execute(
                "UPDATE session_players SET visited_nodes_json = ? WHERE session_id = ? AND user_id = ?",
                (json.dumps(visited), session["id"], user_id),
            )
            self.set_die(conn, session["id"], user_id, 2)
            moved = move_in_session(conn, user_id, session["code"], "LIL")

        self.assertEqual(session["game_mode"], "tour_europe")
        self.assertIn(moved["session"]["status"], {"closing", "finished"})
        self.assertGreaterEqual(moved["session"]["me"]["visited_countries_count"], 12)

    def test_session_move_advances_turn_and_uses_session_progress(self):
        with self.db.session() as conn:
            first = register(conn, "turn1@example.com", "secret123", "Turn1")
            second = register(conn, "turn2@example.com", "secret123", "Turn2")
            session = create_session(conn, first["user"]["id"], "Turn road")
            join_session(conn, second["user"]["id"], session["code"])
            started = start_session(conn, first["user"]["id"], session["code"])
            self.choose_initial_trajets(conn, started, first["user"]["id"])
            self.set_die(conn, session["id"], first["user"]["id"])
            moved = move_in_session(conn, first["user"]["id"], session["code"], "LYO")

        self.assertEqual(moved["session"]["current_turn_user_id"], first["user"]["id"])
        self.assertEqual(moved["session"]["players"][0]["current_node_id"], "LYO")
        self.assertEqual(moved["session"]["players"][0]["dice_remaining"], 1)
        self.assertEqual(moved["session"]["players"][0]["board_position"]["kind"], "city")
        self.assertLess(moved["session"]["players"][0]["durability"], 100)
        self.assertGreater(moved["move"]["durability_cost"], 0)

    def test_session_player_can_turn_back_on_current_route(self):
        with self.db.session() as conn:
            first = register(conn, "turnback@example.com", "secret123", "Back")
            session = create_session(conn, first["user"]["id"], "Turn back")
            started = start_session(conn, first["user"]["id"], session["code"])
            self.choose_initial_trajets(conn, started, first["user"]["id"])
            self.set_die(conn, session["id"], first["user"]["id"], 2)
            outbound = move_in_session(conn, first["user"]["id"], session["code"], "LYO")
            self.set_die(conn, session["id"], first["user"]["id"], 2)
            returned = move_in_session(conn, first["user"]["id"], session["code"], "PAR")

        self.assertEqual(outbound["session"]["me"]["board_position"]["kind"], "route")
        self.assertEqual(returned["session"]["me"]["current_node_id"], "PAR")
        self.assertEqual(returned["session"]["me"]["board_position"]["kind"], "city")

    def test_public_contract_is_claimed_on_target_city(self):
        with self.db.session() as conn:
            result = register(conn, "contract@example.com", "secret123", "Contract")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "Contract room")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            conn.execute(
                """
                INSERT INTO session_contracts
                  (session_id, title, description, target_node_id, reward_coins, reward_victory_points, reward_xp, created_round, expires_round)
                VALUES (?, 'Contrat test', 'Rejoindre Lille.', 'LIL', 40, 9, 12, 1, 3)
                """,
                (session["id"],),
            )
            self.set_die(conn, session["id"], user_id, 2)
            moved = move_in_session(conn, user_id, session["code"], "LIL")
            contract = next(contract for contract in moved["session"]["contracts"] if contract["title"] == "Contrat test")

        self.assertEqual(contract["status"], "claimed")
        self.assertEqual(contract["claimed_by_user_id"], user_id)
        self.assertGreaterEqual(moved["session"]["me"]["victory_points"], 9)
        self.assertTrue(moved["claimed_contracts"])

    def test_player_interaction_can_gift_coins(self):
        with self.db.session() as conn:
            first = register(conn, "gift1@example.com", "secret123", "Gift1")
            second = register(conn, "gift2@example.com", "secret123", "Gift2")
            session = create_session(conn, first["user"]["id"], "Gift room")
            join_session(conn, second["user"]["id"], session["code"])
            started = start_session(conn, first["user"]["id"], session["code"])
            self.choose_initial_trajets(conn, started, first["user"]["id"])
            result = player_interaction(conn, first["user"]["id"], session["code"], second["user"]["id"], "gift_coins")

        giver = next(player for player in result["session"]["players"] if player["user_id"] == first["user"]["id"])
        receiver = next(player for player in result["session"]["players"] if player["user_id"] == second["user"]["id"])
        self.assertEqual(giver["coins"], 130)
        self.assertEqual(receiver["coins"], 150)

    def test_session_task_rewards_and_advances_turn(self):
        with self.db.session() as conn:
            first = register(conn, "task1@example.com", "secret123", "Task1")
            second = register(conn, "task2@example.com", "secret123", "Task2")
            session = create_session(conn, first["user"]["id"], "Tasks")
            join_session(conn, second["user"]["id"], session["code"])
            started = start_session(conn, first["user"]["id"], session["code"])
            self.choose_initial_trajets(conn, started, first["user"]["id"])
            activated = activate_task(conn, first["user"]["id"], session["code"], "courses")
            result = complete_task(conn, first["user"]["id"], session["code"], "courses")

        self.assertEqual(len(activated["session"]["missions"]["active"]), 1)
        self.assertEqual(result["session"]["players"][0]["coins"], 190)
        self.assertEqual(len(result["session"]["missions"]["completed"]), 1)
        self.assertEqual(result["progression"]["coins"], 0)
        self.assertEqual(result["session"]["current_turn_user_id"], second["user"]["id"])

    def test_difficult_mission_blocks_next_turn_without_fuel_cost(self):
        with self.db.session() as conn:
            result = register(conn, "lockmission@example.com", "secret123", "Lock")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "Locked mission")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            before = conn.execute("SELECT fuel FROM session_players WHERE session_id = ? AND user_id = ?", (session["id"], user_id)).fetchone()["fuel"]
            activate_task(conn, user_id, session["code"], "courses")
            completed = complete_task(conn, user_id, session["code"], "courses")

            self.assertEqual(completed["session"]["me"]["fuel"], before)
            self.assertEqual(completed["session"]["me"]["mission_locked_turns"], 1)
            with self.assertRaises(ApiError):
                move_in_session(conn, user_id, session["code"], "LYO")
            unlocked = finish_turn(conn, user_id, session["code"])

        self.assertEqual(unlocked["me"]["mission_locked_turns"], 0)

    def test_session_only_one_active_mission(self):
        with self.db.session() as conn:
            first = register(conn, "mission1@example.com", "secret123", "Mission1")
            session = create_session(conn, first["user"]["id"], "Missions")
            started = start_session(conn, first["user"]["id"], session["code"])
            self.choose_initial_trajets(conn, started, first["user"]["id"])
            activate_task(conn, first["user"]["id"], session["code"], "courses")
            with self.assertRaises(Exception):
                activate_task(conn, first["user"]["id"], session["code"], "capitale")

    def test_capital_carpool_mission_teleports_to_nearest_capital(self):
        with self.db.session() as conn:
            result = register(conn, "capitalhop@example.com", "secret123", "Hop")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "Capital hop")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            activated = activate_task(conn, user_id, session["code"], "capitale")
            target = activated["task"]["target_node_id"]
            completed = complete_task(conn, user_id, session["code"], "capitale")

        self.assertEqual(completed["session"]["me"]["current_node_id"], target)
        self.assertIn(target, completed["session"]["me"]["visited_nodes"])

    def test_non_capital_city_can_offer_local_mission(self):
        with self.db.session() as conn:
            result = register(conn, "noncapitalmission@example.com", "secret123", "Local")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "Local mission")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            self.set_die(conn, session["id"], user_id, 2)
            moved = move_in_session(conn, user_id, session["code"], "LIL")
            task = moved["session"]["current_city_state"]["tasks"][0]
            activated = activate_task(conn, user_id, session["code"], task["difficulty"])

        self.assertEqual(len(activated["session"]["missions"]["active"]), 1)
        self.assertNotEqual(activated["session"]["missions"]["active"][0]["origin_node_id"], "PAR")

    def test_leave_last_player_deletes_session(self):
        with self.db.session() as conn:
            result = register(conn, "leave@example.com", "secret123", "Leave")
            session = create_session(conn, result["user"]["id"], "Gone")
            leave_session(conn, result["user"]["id"], session["code"])
            remaining = conn.execute("SELECT 1 FROM game_sessions WHERE code = ?", (session["code"],)).fetchone()

        self.assertIsNone(remaining)

    def test_station_does_not_auto_refuel_on_arrival(self):
        with self.db.session() as conn:
            result = register(conn, "station@example.com", "secret123", "Station")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "Manual fuel")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            conn.execute(
                "UPDATE session_city_states SET feature_type = 'station', feature_payload_json = ? WHERE session_id = ? AND node_id = 'LIL'",
                ('{"fuel_price": 10, "fuel_to": 35}', session["id"]),
            )
            road = conn.execute(
                "SELECT * FROM roads WHERE (from_node_id = 'PAR' AND to_node_id = 'LIL') OR (from_node_id = 'LIL' AND to_node_id = 'PAR')"
            ).fetchone()
            self.set_die(conn, session["id"], user_id, 2)
            moved = move_in_session(conn, user_id, session["code"], "LIL")

        self.assertLess(moved["session"]["me"]["coins"], 140)
        self.assertLess(moved["session"]["me"]["fuel"], 35)

    def test_garage_restores_durability(self):
        with self.db.session() as conn:
            result = register(conn, "durability@example.com", "secret123", "Durability")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "Garage")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            conn.execute("UPDATE session_players SET durability = 42 WHERE session_id = ? AND user_id = ?", (session["id"], user_id))
            repaired = use_city_service(conn, user_id, session["code"], "garage")

        self.assertEqual(repaired["session"]["me"]["durability"], 100)
        self.assertLess(repaired["session"]["me"]["coins"], 140)

    def test_bonus_malus_draws_once_per_city_passage(self):
        with self.db.session() as conn:
            result = register(conn, "citycard@example.com", "secret123", "CityCard")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "City cards")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            conn.execute(
                "UPDATE session_city_states SET feature_type = 'card', feature_payload_json = '{}' WHERE session_id = ? AND node_id = 'LIL'",
                (session["id"],),
            )
            self.set_die(conn, session["id"], user_id, 2)
            move_in_session(conn, user_id, session["code"], "LIL")
            self.set_die(conn, session["id"], user_id, 2)
            move_in_session(conn, user_id, session["code"], "PAR")
            self.set_die(conn, session["id"], user_id, 2)
            move_in_session(conn, user_id, session["code"], "LIL")
            specials = [
                card for card in get_user_inventory(conn, user_id)
                if card["status"] == "active" and card["type"] in ("bonus", "malus")
            ]

        self.assertEqual(len(specials), 2)

    def test_radar_card_must_be_paid_in_capital(self):
        with self.db.session() as conn:
            result = register(conn, "radarcard@example.com", "secret123", "Radar")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "Radar card")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            inventory_id = self.add_session_card(conn, user_id, session["id"], "radar")
            applied = apply_session_special_card(conn, user_id, session["code"], inventory_id)

        self.assertEqual(applied["session"]["me"]["coins"], 105)
        self.assertTrue(any(card["inventory_id"] == inventory_id and card["status"] == "completed" for card in applied["inventory"]))

    def test_mechanical_malus_ticks_and_garage_resolves_it(self):
        with self.db.session() as conn:
            result = register(conn, "flatcard@example.com", "secret123", "Flat")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "Flat tire")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            inventory_id = self.add_session_card(conn, user_id, session["id"], "crevaison")
            ticked = finish_turn(conn, user_id, session["code"])
            repaired = use_city_service(conn, user_id, session["code"], "garage")
            card = next(card for card in get_user_inventory(conn, user_id) if card["inventory_id"] == inventory_id)

        self.assertEqual(ticked["me"]["durability"], 95)
        self.assertEqual(repaired["session"]["me"]["durability"], 100)
        self.assertEqual(card["status"], "completed")

    def test_fuel_modifier_cards_affect_movement_and_expire(self):
        with self.db.session() as conn:
            result = register(conn, "fuelcard@example.com", "secret123", "Fuel")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "Bad fuel")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            conn.execute(
                "UPDATE session_city_states SET feature_type = 'tasks', feature_payload_json = '{}' WHERE session_id = ? AND node_id = 'LIL'",
                (session["id"],),
            )
            inventory_id = self.add_session_card(conn, user_id, session["id"], "essence-contaminee", quantity=2)
            self.set_die(conn, session["id"], user_id, 2)
            moved = move_in_session(conn, user_id, session["code"], "LIL")
            finish_turn(conn, user_id, session["code"])
            card = next(card for card in get_user_inventory(conn, user_id) if card["inventory_id"] == inventory_id)

        self.assertEqual(moved["session"]["me"]["fuel"], 31)
        self.assertEqual(card["status"], "completed")

    def test_only_one_active_carpooler_per_player(self):
        with self.db.session() as conn:
            result = register(conn, "carpool@example.com", "secret123", "Carpool")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "Carpool")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            rows = conn.execute("SELECT id FROM session_carpoolers WHERE session_id = ? ORDER BY id LIMIT 2", (session["id"],)).fetchall()
            conn.execute("UPDATE session_carpoolers SET start_node_id = 'PAR' WHERE id IN (?, ?)", (rows[0]["id"], rows[1]["id"]))
            accept_carpooler(conn, user_id, session["code"], rows[0]["id"])
            with self.assertRaises(ApiError):
                accept_carpooler(conn, user_id, session["code"], rows[1]["id"])

    def test_carpooler_must_be_met_at_start_city(self):
        with self.db.session() as conn:
            result = register(conn, "meetcarpool@example.com", "secret123", "Meet")
            user_id = result["user"]["id"]
            session = create_session(conn, user_id, "Meet carpool")
            started = start_session(conn, user_id, session["code"])
            self.choose_initial_trajets(conn, started, user_id)
            row = conn.execute("SELECT id FROM session_carpoolers WHERE session_id = ? ORDER BY id LIMIT 1", (session["id"],)).fetchone()
            conn.execute("UPDATE session_carpoolers SET start_node_id = 'LIL', destination_node_id = 'BRU' WHERE id = ?", (row["id"],))

            with self.assertRaises(ApiError):
                accept_carpooler(conn, user_id, session["code"], row["id"])

            self.set_die(conn, session["id"], user_id, 2)
            moved = move_in_session(conn, user_id, session["code"], "LIL")
            accepted = accept_carpooler(conn, user_id, session["code"], row["id"])

        accepted_row = next(item for item in accepted["carpoolers"] if item["id"] == row["id"])
        self.assertEqual(moved["carpooler"]["id"], row["id"])
        self.assertEqual(accepted_row["status"], "active")

    def test_carpoolers_have_dynamic_rewards(self):
        with self.db.session() as conn:
            result = register(conn, "dynamiccarpool@example.com", "secret123", "Dynamic")
            session = create_session(conn, result["user"]["id"], "Dynamic carpool")
            started = start_session(conn, result["user"]["id"], session["code"])
            self.choose_initial_trajets(conn, started, result["user"]["id"])
            rows = conn.execute(
                "SELECT start_node_id, destination_node_id, victory_points, reward_coins, reward_durability FROM session_carpoolers WHERE session_id = ?",
                (session["id"],),
            ).fetchall()

        self.assertEqual(len(rows), 4)
        self.assertGreater(len({(row["start_node_id"], row["destination_node_id"], row["reward_coins"]) for row in rows}), 1)
        self.assertTrue(all(row["reward_coins"] > 0 for row in rows))

    def test_session_start_offers_five_trajets_then_activates_three(self):
        with self.db.session() as conn:
            result = register(conn, "cleanstart@example.com", "secret123", "Clean")
            draw_special_cards(conn, result["user"]["id"], 2)
            session = create_session(conn, result["user"]["id"], "Clean start")
            started = start_session(conn, result["user"]["id"], session["code"])
            choices = started["starting_trajet_choices"]
            before_active = [card for card in get_user_inventory(conn, result["user"]["id"]) if card["status"] == "active"]
            chosen = self.choose_initial_trajets(conn, started, result["user"]["id"])
            active = [card for card in get_user_inventory(conn, result["user"]["id"]) if card["status"] == "active"]
            archived = [card for card in get_user_inventory(conn, result["user"]["id"]) if card["status"] == "archived" and card["type"] == "trajet" and card["session_id"] == session["id"]]

        self.assertEqual(len(choices), 5)
        self.assertEqual(len([card for card in choices if card["trajet"]["kind"] == "court"]), 3)
        self.assertEqual(len([card for card in choices if card["trajet"]["kind"] == "long"]), 2)
        self.assertTrue(any(card["trajet"]["city_ids"][0] == "PAR" and card["trajet"]["kind"] == "court" for card in choices))
        self.assertEqual(before_active, [])
        self.assertEqual(len(chosen["chosen"]), 3)
        self.assertEqual(len(active), 3)
        self.assertEqual(started["me"]["fuel"], 35)
        self.assertTrue(all(card["type"] == "trajet" for card in active))
        self.assertTrue(all(card["session_id"] == session["id"] for card in active))
        self.assertEqual(len(archived), 2)
        self.assertFalse(chosen["session"]["needs_starting_trajet_choice"])

    def test_new_session_starts_every_player_at_zero_points(self):
        with self.db.session() as conn:
            first = register(conn, "zero1@example.com", "secret123", "Zero1")
            second = register(conn, "zero2@example.com", "secret123", "Zero2")
            session = create_session(conn, first["user"]["id"], "Zero score")
            join_session(conn, second["user"]["id"], session["code"])
            conn.execute(
                "UPDATE session_players SET victory_points = 45, completed_trajets = 3, distance_km = 900, xp = 120 WHERE session_id = ?",
                (session["id"],),
            )
            started = start_session(conn, first["user"]["id"], session["code"])

        self.assertTrue(all(player["victory_points"] == 0 for player in started["players"]))
        self.assertTrue(all(player["completed_trajets"] == 0 for player in started["players"]))
        self.assertTrue(all(row["score"] == 0 for row in started["leaderboard"]))

    def test_debug_join_code_is_removed(self):
        with self.db.session() as conn:
            result = register(conn, "nodebug@example.com", "secret123", "NoDebug")

            with self.assertRaises(ApiError):
                join_session(conn, result["user"]["id"], "DEBUG")


if __name__ == "__main__":
    unittest.main()
