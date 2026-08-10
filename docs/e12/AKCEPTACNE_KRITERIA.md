# AC-01 až AC-33 – mapa požiadaviek a dôkazov

Táto tabuľka mapuje kapitolu 24 `ZADANIE.md` na konkrétny automatizovaný,
staging alebo ľudský dôkaz. Označenie „splnené lokálne“ neznamená produkčný
cutover. Externé podpisy a reálna prevádzka zostávajú riadené bránami E12–E14.

| ID | Akceptačné kritérium | Primárny dôkaz | Stav |
|---|---|---|---|
| AC-01 | Automatický 14-dňový zoradený prehľad bez redakcie | `test_publication_composer.py::test_sorting_is_deterministic_with_info_all_day_sources_and_manual`, `test_publication_draft_service.py` | splnené lokálne |
| AC-02 | Automatický deň, dátum, čas a day emoji | `test_domain_time.py`, `test_publication_composer.py::test_composer_slot_and_window_are_stable_across_dst` a formatting scenáre | splnené lokálne |
| AC-03 | Titulok/popis pretrvá sync aj reštart | `test_calendar_sync.py::test_repeat_full_sync_preserves_internal_uuid_and_editor_override`, PostgreSQL persistence, full-stack Playwright save/reload/API read | splnené lokálne |
| AC-04 | Úprava sa použije v oboch týždenných publikáciách | composer series/instance matica, Playwright scenár 04, E12 `SHADOW_CYKLY.md` rehearsal | splnené lokálne |
| AC-05 | Zrušenie vlastnej úpravy obnoví Google hodnotu | `test_event_editor.py` instance/series description-state scenáre, composer priority matica | splnené lokálne |
| AC-06 | Manuálna udalosť sa zaradí podľa času | `test_publication_composer.py::test_sorting_is_deterministic_with_info_all_day_sources_and_manual`, Playwright scenár 05 | splnené lokálne |
| AC-07 | INFO platnosť je inkluzívna, expirovaný záznam ostáva v histórii | `test_publication_composer.py::test_info_validity_manual_event_and_url_warnings`, `test_legacy_migration_import.py::test_import_is_idempotent_and_preserves_expired_history`, Playwright scenár 06 | splnené lokálne |
| AC-08 | Editor zobrazuje najbližší publikačný termín | `App.test.tsx`, Playwright scenáre 01–04 | splnené lokálne |
| AC-09 | Web a Discord používajú jeden formátovací model | kanonický `PublicationDraft`, composer snapshot test, `App.test.tsx` Discord preview | splnené lokálne |
| AC-10 | Automatický termín sa publikuje najviac raz | `test_publication_engine.py::test_due_scheduler_publishes_once_with_fresh_calendar` a `test_two_scheduler_instances_cannot_duplicate_the_same_slot` | splnené lokálne |
| AC-11 | Úspešný manuálny publish preskočí práve jeden termín | `test_publication_engine.py::test_successful_manual_run_skips_exactly_the_same_scheduler_slot`, Playwright scenár 07 | splnené lokálne |
| AC-12 | Neúspešný manuálny publish termín nepreskočí | publication engine failure/retry testy a stavový invariant úspešného slotu | splnené lokálne |
| AC-13 | Veľký balík sa bezpečne rozdelí | `test_publication_composer.py::test_message_plan_splits_on_total_characters_and_rejects_item_limit`, engine test s viac než 10 udalosťami | splnené lokálne |
| AC-14 | Team Mod nevykoná Admin operáciu | `test_api_authorization_matrix.py`, `test_settings.py::test_team_mod_cannot_open_settings` | splnené lokálne |
| AC-15 | API ani cudzie tlačidlo neobídu oprávnenie | `test_api_authorization_matrix.py`, `test_discord_views.py`, Playwright scenár 11 | splnené lokálne |
| AC-16 | Potvrdenie archivuje iba konkrétny kanál | `test_channels.py::test_archive_request_is_single_use_and_requires_fresh_admin_authorization`, Playwright scenár 09 | splnené lokálne |
| AC-17 | Roly používajú Discord ID a rešpektujú hierarchiu | `test_settings.py::test_role_management_protects_last_admin_and_uses_configured_roles`, Discord gateway testy, Playwright scenár 10 | splnené lokálne |
| AC-18 | Seen a automatické reakcie sa konfigurujú a validujú vo webe | `test_settings.py::test_calendar_identity_reset_and_reaction_round_trip`, `test_discord_admin_gateway.py`, `App.test.tsx` Settings workspace | splnené lokálne |
| AC-19 | Chyba má zrozumiteľný výsledok | jednotné API problem responses, UI error boundary/form errors, publication/Discord response testy | splnené lokálne |
| AC-20 | Citlivé zmeny sú v audite | editor/settings/channels/roles/migration integračné testy a `test_content_editor.py::test_audit_query_is_guild_isolated_and_role_filtered` | splnené lokálne |
| AC-21 | Mobile, tablet a počítač sú plne použiteľné | 17 mockovaných a 1 full-stack Playwright scenár v desktop profile a Pixel 7; overflow, keyboard/focus a reduced-motion testy | **otvorené pre ľudský tablet/200 % zoom UAT** |
| AC-22 | Kritické dátumy, roly a publikovanie majú automatické testy | backend unit/integration suite, Vitest a Playwright | splnené lokálne |
| AC-23 | Nasadenie, backup/restore a recovery sú zdokumentované | `docs/e13/`, `docs/PREVADZKOVY_MANUAL_ZLYHANE_PUBLIKOVANIE.md`, `docs/e11/BACKUP_RESTORE_TEST.md` | splnené lokálne |
| AC-24 | Default pondelok 20:00, deň/čas nastaviteľný | konfiguračné/doménové testy, settings integračné testy a web Settings | splnené lokálne |
| AC-25 | Google popis je defaultne vypnutý a globálne zapínateľný | composer priority matica, settings integračné testy | splnené lokálne |
| AC-26 | Editor predvyplní Google popis bez automatického uloženia | `App.test.tsx` recurring editor a EventEditorPanel správanie | splnené lokálne |
| AC-27 | `@everyone` je v úspešnej publikácii práve raz | `test_publication_composer.py::test_message_plan_respects_limits_everyone_nonce_and_seen_target` a legacy-defense test, DB CHECK migrácia | splnené lokálne |
| AC-28 | Generovaný úvod má deterministický fallback | `test_publication_intro.py::test_generator_failure_uses_deterministic_slovak_fallback` | splnené lokálne |
| AC-29 | `stop carlo` vylúči, ostane v editore a Admin ho môže zaradiť | Calendar domain/composer testy a Playwright scenár 12 | splnené lokálne |
| AC-30 | Recurring rozlišuje výskyt a tento + budúce | `test_event_editor.py::test_series_updates_apply_from_occurrence_and_are_versioned`, composer series testy, Playwright scenár 13 | splnené lokálne |
| AC-31 | Ručne publikuje iba Admin alebo SDB/FMA | capability/API matica, manual publication policy test, Playwright scenáre 07 a 14 | splnené lokálne |
| AC-32 | Archív prevezme oprávnenia archívnej kategórie | channel service/recovery integračné testy a Discord archive gateway | splnené lokálne |
| AC-33 | Alerty smerujú do moderátorského kanála | `test_settings.py::test_alert_category_toggle_is_enforced_at_delivery`, scheduler/incident alert integračné testy | splnené lokálne |

## Otvorený dôkaz

Jediné kritérium, ktoré nemožno uzavrieť iba automatizáciou, je AC-21. Admin,
Team Mod a SDB/FMA musia podpísať príslušné body `UAT_CHECKLIST.md` na reálnych
desktop/tablet/mobile zariadeniach vrátane 200 % zoomu. Automatizované browserové
testy zostávajú regresnou poistkou, nie náhradou ľudského posúdenia čitateľnosti.
