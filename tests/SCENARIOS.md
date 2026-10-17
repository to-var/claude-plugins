# tovar test scenarios

One row per thing a user does, what must happen, and the tests that prove it.
"(added)" marks a row that was a gap before this map and now has a test.
"Not testable here" rows say why; the hand checks for them live in
`tests/SMOKE_TESTS.md`.

How to run everything:

```
python3 -m unittest discover -s tests
claude plugin test tovar-core
claude plugin test tovar-mods
claude plugin validate .
python3 tools/tovar-mods.py check
```

Python test names are `file > Class.test_name`. Plugin test names are
`file > test title`; in `tovar-mods/tests/bar.test.tsx` every per-bar title
runs once for each bar (`legendary-birds: ...`, `smash-bros: ...`), and every
drawing test mounts on both the `terminal` and `desktop` surfaces.

## tovar-core engine: themes

| User does | Must happen | Tests |
|---|---|---|
| `theme list` | Yours and examples listed, sorted, yours hides an example of the same name, active one marked | test_tovar_theme > ReadShowCheckExportTest.test_list_marks_yours_and_examples; test_tovar_items > AreaTest.test_yours_hides_the_example_with_the_same_name, AreaTest.test_entries_are_sorted_by_name, HelpersTest.test_list_result_marks_active_items; test_tovar_cli > CliTest.test_json_output_is_machine_readable |
| `theme show <name>` | Display name, source, label and a sample of each list | test_tovar_theme > ReadShowCheckExportTest.test_show_summarises; test_tovar_cli > CliTest.test_accents_print_without_crashing |
| `theme check [names]` | Every rule broken is listed, exit 1 on failure; no names checks yours and examples | test_tovar_theme > RulesTest.test_problems_lists_every_broken_rule, ReadShowCheckExportTest.test_check_passes_and_fails; test_tovar_cli > CliTest.test_failed_check_exits_one_and_still_prints; test_tovar_scenarios > ThemeLifecycleTest.test_check_with_no_names_checks_yours_and_examples (added) |
| Shipped example themes | Every example passes check and applies | test_tovar_scenarios > ThemeLifecycleTest.test_shipped_example_themes_pass_check_and_apply (added) |
| `theme read <source>` (import preview) | Folder, settings file or theme.json printed as JSON, nothing written; bad source explained | test_tovar_theme > ReadShowCheckExportTest.test_read_prints_any_source_as_json_and_writes_nothing, ReadShowCheckExportTest.test_read_of_a_bad_source_explains |
| `theme create --file` | Three files saved with the five plugin tips; folder, settings file and theme.json all accepted; problems save nothing | test_tovar_theme > CreateTest.test_create_saves_three_files_with_plugin_tips, CreateTest.test_create_takes_a_theme_folder_a_settings_file_and_a_theme_json, CreateTest.test_create_with_problems_saves_nothing_and_lists_them, CreateTest.test_a_settings_file_without_names_is_reported_not_half_saved, CreateTest.test_create_dry_run_writes_nothing |
| `theme create --from <example>` | Copy of the example becomes yours | test_tovar_theme > CreateTest.test_create_from_an_example_copies_it |
| `theme create` with no source or both | Clear error | test_tovar_theme > CreateTest.test_create_needs_a_source_and_refuses_two |
| `theme update` | Yours replaced and backed up; active theme told to apply again; changes reach settings only after apply | test_tovar_theme > ChangeTest.test_update_replaces_your_theme_and_backs_up, ChangeTest.test_update_of_the_active_theme_says_to_apply_again; test_tovar_scenarios > ThemeLifecycleTest.test_an_updated_active_theme_reaches_settings_only_after_apply (added) |
| `theme update` of an example | Refused | test_tovar_theme > ChangeTest.test_update_refuses_examples |
| `theme delete` | Yours removed with a backup; active refused; example refused | test_tovar_theme > ChangeTest.test_delete_removes_yours_and_refuses_examples, ChangeTest.test_delete_of_the_active_theme_is_refused; test_tovar_items > AreaTest.test_delete_backs_up_so_restore_brings_it_back, AreaTest.test_deleting_a_folder_item_removes_the_folder |
| `theme export --to` | Portable folder written; non-empty target and missing `--to` refused; dry run writes nothing | test_tovar_theme > ReadShowCheckExportTest.test_export_writes_a_portable_folder_and_refuses_a_full_one; test_tovar_scenarios > ThemeLifecycleTest.test_export_dry_run_writes_nothing (added) |
| `theme apply --dry-run` | Diff shown, nothing written, state unchanged | test_tovar_theme_apply > ApplyTest.test_apply_dry_run_changes_nothing; test_tovar_scenarios > ThemeLifecycleTest.test_apply_dry_run_shows_the_settings_diff (added); test_tovar_cli > CliTest.test_create_apply_status_off_through_the_command_line |
| `theme apply` | Three settings keys, tips file and names file written; backup made; restart reminder | test_tovar_theme_apply > ApplyTest.test_apply_writes_the_three_keys_the_tips_and_names, ApplyTest.test_apply_backs_up_the_settings_file; test_tovar_scenarios > ThemeLifecycleTest.test_apply_writes_every_name_and_tip_to_the_active_folder (added) |
| Apply on a missing settings file | File created | test_tovar_theme_apply > ApplyTest.test_apply_creates_the_settings_file_when_missing |
| Apply on an empty settings file | Treated as no settings: theme written, empty file backed up and restorable | test_tovar_scenarios > ThemeSettingsFileTest.test_apply_on_an_empty_settings_file_writes_the_theme, ThemeSettingsFileTest.test_apply_backs_up_an_empty_settings_file_so_undo_brings_it_back, ThemeSettingsFileTest.test_off_and_status_on_an_empty_settings_file_change_nothing (added, was a bug) |
| Apply on settings with unrelated keys | Other keys and their order kept, off puts them back exactly | test_tovar_theme_apply > ApplyTest.test_apply_keeps_other_settings_and_key_order, ApplyTest.test_off_removes_only_the_three_keys; test_tovar_scenarios > ThemeSettingsFileTest.test_apply_and_off_keep_unrelated_keys_exactly (added) |
| Apply twice / switch theme | Second apply changes nothing; switching replaces values | test_tovar_theme_apply > ApplyTest.test_apply_twice_changes_nothing_the_second_time, ApplyTest.test_switching_themes_replaces_the_values |
| Apply an unknown theme | Clear error | test_tovar_theme_apply > ApplyTest.test_apply_an_unknown_theme_is_a_clear_error |
| Plugin tips | Five fresh plugin tips first, old ones swapped, regenerated when the display name changes | test_tovar_theme > RulesTest.test_normalize_adds_five_plugin_tips_first_and_keeps_facts, RulesTest.test_normalize_swaps_old_plugin_tips_for_fresh_ones; test_tovar_scenarios > ThemeLifecycleTest.test_update_with_a_new_display_regenerates_the_plugin_tips (added) |
| `theme off` | Only the three keys removed, names and tips files deleted; nothing active means nothing changed; a theme tovar did not write is left alone | test_tovar_theme_apply > ApplyTest.test_off_removes_only_the_three_keys, ApplyTest.test_off_when_nothing_is_active_changes_nothing, ApplyTest.test_off_leaves_a_theme_that_tovar_did_not_write |
| `theme active` | Applied theme as JSON, works without a data folder, foreign tips file and none are errors, junk entries dropped | test_tovar_theme_active > ActiveTest (all six tests) |
| Active detection after restore or hand edit | Read from the real settings file, never stale state | test_tovar_theme_apply > ApplyTest.test_active_name_follows_the_real_settings_after_a_restore, ApplyTest.test_restore_to_a_different_theme_makes_that_theme_active_again, ApplyTest.test_a_settings_file_that_points_at_another_folder_is_not_ours, ActiveNameTest (both tests) |
| Accented text | Survives create, read, export and printing | test_tovar_theme > CreateTest.test_accents_survive_create_read_and_export; test_tovar_cli > CliTest.test_accents_print_without_crashing |

## tovar-core engine: styles

| User does | Must happen | Tests |
|---|---|---|
| `style create --file / --from` | Saved when frontmatter name, description and body exist; bad drafts refused | test_tovar_style > StyleTest.test_create_saves_the_file_and_refuses_bad_ones, StyleTest.test_create_from_an_example, RulesTest.test_frontmatter_parses, RulesTest.test_problems |
| `style update` | Yours replaced; active one told to apply again; examples refused | test_tovar_style > StyleTest.test_update_and_delete_rules, StyleTest.test_examples_cannot_be_updated_or_deleted |
| `style delete` | Active refused, examples refused, yours removed | test_tovar_style > StyleTest.test_update_and_delete_rules, StyleTest.test_examples_cannot_be_updated_or_deleted |
| `style apply` | `tovar-<name>.md` written to output-styles and `outputStyle` set; dry run and broken settings change nothing; switching removes the old file | test_tovar_style > StyleTest.test_apply_writes_the_style_file_and_the_setting, StyleTest.test_apply_dry_run_and_invalid_settings_change_nothing, StyleTest.test_apply_twice_changes_nothing_and_switching_removes_the_old_file |
| Apply on an empty settings file | Works, only `outputStyle` written | test_tovar_scenarios > StyleScenarioTest.test_apply_on_an_empty_settings_file (added, was a bug) |
| `style off` | File and setting removed only when tovar owns them; user's later pick and own files left alone; dry run changes nothing; broken settings untouched | test_tovar_style > StyleTest.test_off_removes_the_file_and_the_setting_only_if_tovar_owns_it, StyleTest.test_off_leaves_a_style_the_user_picked_later; test_tovar_scenarios > StyleScenarioTest.test_off_never_touches_the_users_own_style_files, StyleScenarioTest.test_off_dry_run_changes_nothing, StyleScenarioTest.test_off_leaves_a_broken_settings_file_untouched (added) |
| Active detection | Only a `tovar-` file whose frontmatter name equals `outputStyle`; follows restores | test_tovar_scenarios > StyleScenarioTest.test_active_needs_the_tovar_prefix_and_a_matching_frontmatter_name (added); test_tovar_style > StyleTest.test_active_name_follows_a_restore, StyleTest.test_restore_to_the_previous_style_makes_it_active_again |
| `style show / check / list` | Text shown, check fails on a broken file | test_tovar_style > StyleTest.test_show_check_list |

## tovar-core engine: memory

| User does | Must happen | Tests |
|---|---|---|
| `memory create --file / --from` | Saved; empty, marker-holding and marker-named snippets refused | test_tovar_memory > MemoryTest.test_create_from_example_show_check_list, MemoryTest.test_snippets_named_like_a_marker_are_refused, MemoryTest.test_snippets_with_tovar_markers_or_no_text_are_refused |
| `memory enable` | Block written, your text kept, missing CLAUDE.md created, twice changes nothing, unknown snippet a clear error | test_tovar_memory > MemoryTest.test_enable_writes_the_block_and_keeps_your_text, MemoryTest.test_enable_creates_a_missing_claude_md, MemoryTest.test_enable_twice_and_disable_when_off_change_nothing; test_tovar_scenarios > MemoryScenarioTest.test_enable_of_an_unknown_snippet_is_a_clear_error (added) |
| `memory disable` | Snippet removed, text around kept, last one leaves the file empty | test_tovar_memory > MemoryTest.test_enable_in_order_disable_and_reorder, MergeTest.test_removing_keeps_the_text_around_it |
| `memory order` | Reorders; must list exactly the enabled ones | test_tovar_memory > MemoryTest.test_enable_in_order_disable_and_reorder, MemoryTest.test_order_must_list_exactly_the_enabled_snippets |
| `memory apply` | Writes edited snippets; nothing enabled leaves CLAUDE.md alone; missing snippet a clear error | test_tovar_memory > MemoryTest.test_update_of_an_enabled_snippet_needs_apply_to_reach_claude_md, MemoryTest.test_a_missing_enabled_snippet_is_a_clear_error; test_tovar_scenarios > MemoryScenarioTest.test_apply_with_nothing_enabled_leaves_claude_md_alone (added) |
| Text outside the block | Kept byte for byte through enable, order and apply | test_tovar_memory > MergeTest.test_block_in_the_middle_is_replaced_and_outside_text_is_untouched, MergeTest.test_block_is_appended_after_existing_text_that_is_kept; test_tovar_scenarios > MemoryScenarioTest.test_text_outside_the_block_is_kept_byte_for_byte (added) |
| Broken block | Every write refused, file untouched | test_tovar_memory > MergeTest.test_half_or_repeated_or_reversed_markers_stop_the_write, MemoryTest.test_half_markers_in_claude_md_stop_everything; test_tovar_scenarios > MemoryScenarioTest.test_a_broken_block_stops_disable_order_and_apply_too (added) |
| CRLF files | A CRLF CLAUDE.md stays CRLF, CRLF snippets cleaned, round trip back to the original | test_tovar_memory > MergeTest.test_windows_line_endings_are_kept, MergeTest.test_render_orders_snippets_and_cleans_line_endings; test_tovar_core > ApplyChangesTest.test_line_endings_survive_a_round_trip; test_tovar_scenarios > MemoryScenarioTest.test_a_crlf_claude_md_stays_crlf_through_enable_and_disable (added) |
| Dry run | Diff shown, nothing written | test_tovar_memory > MemoryTest.test_dry_run_shows_a_diff_and_writes_nothing |
| `memory delete` | Enabled refused, others removed | test_tovar_memory > MemoryTest.test_delete_of_an_enabled_snippet_is_refused |
| Enabled list after restore | Read from the real CLAUDE.md | test_tovar_memory > MemoryTest.test_enabled_follows_the_real_file_after_a_restore, MemoryTest.test_restore_to_an_earlier_set_shows_the_real_enabled_list |

## tovar-core engine: undo and status

| User does | Must happen | Tests |
|---|---|---|
| `status` | Theme, style, memory and both folders shown; "none" when nothing applied | test_tovar_cli > CliTest.test_create_apply_status_off_through_the_command_line; test_tovar_scenarios > UndoTest.test_status_shows_theme_style_and_memory, UndoTest.test_status_with_nothing_applied (added) |
| `restore` (list) | Backups newest first; "(no backups yet)" when none | test_tovar_cli > CliTest.test_restore_lists_and_restores; test_tovar_scenarios > UndoTest.test_backups_are_listed_newest_first, UndoTest.test_restore_with_no_backups_says_so (added) |
| `restore <name> --dry-run` | Whole diff and a whole-file warning, nothing written | test_tovar_core > ApplyChangesTest.test_restore_dry_run_shows_the_whole_diff; test_tovar_cli > CliTest.test_restore_warns_that_whole_files_are_replaced; test_tovar_scenarios > UndoTest.test_restore_dry_run_writes_nothing (added) |
| `restore <name>` | Old text back, current text backed up first | test_tovar_core > ApplyChangesTest.test_restore_puts_the_old_text_back_and_backs_up_the_current_one; test_tovar_cli > CliTest.test_restore_lists_and_restores |
| Restore of files a change created | They are deleted | test_tovar_core > ApplyChangesTest.test_restore_deletes_files_the_change_created; test_tovar_scenarios > UndoTest.test_restore_after_apply_on_no_settings_deletes_the_created_file (added) |
| Restore of a bad or unknown name | Clear error, no traceback | test_tovar_core > ApplyChangesTest.test_restore_rejects_path_tricks_and_unknown_names; test_tovar_scenarios > UndoTest.test_restore_of_an_unknown_backup_fails_cleanly (added) |

## tovar-core engine: errors

| User does | Must happen | Tests |
|---|---|---|
| Runs without `--data` and without the data variable | Exit 1 naming `--data`, no traceback | test_tovar_core > PathsTest.test_data_dir_needs_the_variable; test_tovar_scenarios > CommandLineErrorTest.test_a_missing_data_folder_is_a_clear_error (added) |
| `--data` given | Replaces the environment | test_tovar_cli > CliTest.test_data_flag_replaces_the_environment |
| Bad item names | Refused in every area, nothing written | test_tovar_items > AreaTest.test_new_names_are_checked; test_tovar_theme > CreateTest.test_create_refuses_a_taken_name_and_bad_names; test_tovar_scenarios > NameRulesTest.test_every_area_refuses_bad_names (added) |
| Missing draft file | Clear error | test_tovar_scenarios > NameRulesTest.test_a_missing_draft_file_is_a_clear_error (added) |
| Unreadable JSON settings | Theme apply, theme off, style apply, style off and status all stop and leave the file untouched | test_tovar_theme_apply > ApplyTest.test_apply_with_invalid_settings_stops_and_changes_nothing; test_tovar_style > StyleTest.test_apply_dry_run_and_invalid_settings_change_nothing; test_tovar_core > ApplyChangesTest.test_invalid_json_names_the_file; test_tovar_scenarios > ThemeSettingsFileTest.test_off_and_status_leave_a_broken_settings_file_untouched, ThemeSettingsFileTest.test_a_settings_file_that_is_not_an_object_is_refused_untouched, StyleScenarioTest.test_off_leaves_a_broken_settings_file_untouched (added) |
| Unknown area, action or missing name | Clear error (parser error for an unknown area) | test_tovar_cli > CliTest.test_unknown_action_and_missing_name_are_clear_errors; test_tovar_items > HelpersTest.test_unknown_action_names_the_valid_ones, HelpersTest.test_one_name_needs_exactly_one; test_tovar_scenarios > CommandLineErrorTest.test_an_area_with_no_action_names_the_actions, CommandLineErrorTest.test_an_unknown_area_is_refused_by_the_parser (added) |
| A file write fails | Reported on stderr, exit 1, no traceback | test_tovar_cli > CliTest.test_a_file_error_is_reported_not_a_traceback, CliTest.test_errors_go_to_stderr_with_exit_code_one |
| Safe writes | Changed files backed up, unchanged skipped, no-backup files not recorded, accents kept | test_tovar_core > ApplyChangesTest (writes, dry run, unchanged, delete, no backup, accents) |

## tovar-core skills

| User does | Must happen | Tests |
|---|---|---|
| Runs any `/tovar-core:*` skill | Each skill has a name and description, every command it shows is a real action and passes `--data`, every action of its area is mentioned, it never says to edit files by hand | test_tovar_skills > SkillsTest (all seven tests) |
| Talks a theme, style or snippet into shape | One question per step, preview, dry run, yes prompt | Not testable here: a skill is a conversation with the model. Hand check in SMOKE_TESTS.md |
| Restarts Claude Code after apply | Spinner verbs, tips, announcements and output style show | Not testable here: needs a real Claude Code restart reading the settings file. Hand check in SMOKE_TESTS.md |

## tovar-core sub-agent names

| User does | Must happen | Tests |
|---|---|---|
| Starts a session | The engine is asked once with `theme active --json`; no command is registered | hooks.test.ts > a session start asks the engine for the active theme and registers no command |
| Spawns sub-agents with a theme applied | Each gets an unused theme name | hooks.test.ts > each sub-agent gets a different name from the theme |
| Spawns more sub-agents than names | Names repeat only after every name was used | hooks.test.ts > names repeat only after every name was used; party.test.ts |
| Spawns a sub-agent with no names or no theme | The description is left alone | hooks.test.ts > with no names, the description is left alone; hooks.test.ts > with no active theme, the description is left alone |
| Engine answer is broken | Treated as no theme | theme-data.test.ts |

## tovar-mods

| User does | Must happen | Tests |
|---|---|---|
| Bar setting `legendary-birds` or `smash-bros` | That bar's characters show, looks read from its own profile files | bar.test.tsx > (per bar) an idle character thinks before the first prompt; the look comes from the bar's own profile files |
| Bar setting `off` | Nothing drawn, no model call, `/tovar-mods:narrate` says how to turn a bar on | bar.test.tsx > off draws nothing and never calls the model |
| Bar setting with an unknown value | Read as the default bar, never "undefined" | bar.test.tsx > an unknown Bar value no-such-bar reads as the default bar; an unknown Bar value toString reads as the default bar; flight.test.ts > only a bar the list really holds is on |
| Session starts | `/tovar-mods:narrate` registered, a random idle character on screen | bar.test.tsx > (per bar) a session start registers /tovar-mods:narrate (added); a new session starts on a random character |
| Prompt sent | Working character and "N tool calls so far" | bar.test.tsx > (per bar) a working character shows while a turn runs |
| Tool call fails | Burning character with the failure count | bar.test.tsx > (per bar) a failed tool call brings on a burning character |
| Tool call denied | Counted as a call ("1 tool calls"), not a failure | bar.test.tsx > (per bar) a denied tool call counts as a call, not a failure (added) |
| Turn ends with Narrate on | Idle character narrates in their color, prompt carries the exchange and profile | bar.test.tsx > (per bar) the character narrates the turn on a second line; the character thinking is the one who gives the summary |
| Narrate setting off | No model call after a turn | bar.test.tsx > (per bar) narration stays off when the setting is off |
| Silent and speaking characters | Silent: sounds then thoughts; speaking: one quoted paragraph | bar.test.tsx > (per bar) silent characters make sounds, then think the summary on the next line; a speaking character always gets one quoted paragraph; narration.test.ts > a silent shape keeps sounds on the first line and thoughts on the second (added) |
| Model gives no answer, fails outright, or answers empty | Facts line stays, no "undefined", no crash, turn result untouched | bar.test.tsx > (per bar) a model that gives no answer keeps the facts line; a model call that fails outright keeps the facts line and the turn; an empty or quotes-only answer keeps the facts line (added) |
| Profile file missing | Default emoji and the mood's color, prompt still sent | bar.test.tsx > (per bar) a missing profile file falls back to the default emoji and mood color (added); narration.test.ts > a profile without emoji or color uses the defaults (added) |
| Model sends very long text | Clipped with an ellipsis | bar.test.tsx > (per bar) a very long narration is clipped (added); narration.test.ts > tidy clips long text to the limit with an ellipsis (added) |
| Model sends markdown or wrapping quotes | Line-start marks, paired emphasis, paired code ticks and wrapping quotes tidied away; lone stars, ticks and underscores (2*3=6, footnote*, __init__, snake_case) kept | bar.test.tsx > (per bar) markdown and wrapping quotes from the model are tidied away (added, was a bug); narration.test.ts > tidy drops markdown and wrapping quotes but keeps snake_case words; tidy keeps lone stars, ticks and underscores, which are facts; tidy drops paired emphasis and a list mark around sounds (added) |
| `/tovar-mods:narrate` | Recap in the character voice; empty session has nothing to say; silent character gets sounds then thoughts; model failure says the voice was lost; works with Narrate off | bar.test.tsx > (per bar) /tovar-mods:narrate recaps the whole session in the character voice; /tovar-mods:narrate with an empty session has nothing to say; /tovar-mods:narrate gives a silent character sounds, then thoughts; /tovar-mods:narrate says so when the model gives no answer; /tovar-mods:narrate says so when the model call fails outright (was a bug); /tovar-mods:narrate still recaps when Narrate is off (added) |
| Helper agent finishes | Nothing changes on the bar | bar.test.tsx > (per bar) a helper agent finishing changes nothing on the bar |
| Next prompt before a narration lands | Late narration dropped | bar.test.tsx > (per bar) a late narration never lands under a newer character |
| Survey shows above the prompt | Bar steps aside | bar.test.tsx > (per bar) the bar steps aside while a survey shows (added) |
| Old or other-bar saved state | Filled in, never "undefined", never leaks | bar.test.tsx > (per bar) state saved by an older version never shows "undefined"; state saved by another bar never leaks in; switching bars mid-session opens on a random character of the new bar; flight.test.ts > state from another bar starts fresh; state with missing fields fills in, never undefined; narration.test.ts > the caption never shows undefined for any mood (added) |
| Many state changes | Shuffled rounds, never the same character twice in a row | bar.test.tsx > (per bar) each state change shows the next character of a shuffled round; flight.test.ts > a round shows every character once, never twice in a row; indexes past the end of a shorter roster are dropped |
| Profile file names | Built from the character name as the script expects | narration.test.ts > slug matches the profile file names (added) |
| `/tovar-mods:narrate` on a long session | Newest text kept, tools named | narration.test.ts > the transcript keeps the newest text and names the tools (added) |
| Changes Bar in `/config` then `/reload-plugins` | New bar shows | Not testable here: the test kit sets options per test and cannot reload a plugin mid-test. Covered per bar by the option tests; hand check in SMOKE_TESTS.md |
| Real Haiku narration quality | Voice fits the profile | Not testable here: needs a live model. Hand check in SMOKE_TESTS.md |

## tools/tovar-mods.py

| User does | Must happen | Tests |
|---|---|---|
| `new <bar> [display]` | Template copied, bar listed in the bar list file and the Bar setting, marketplace untouched, manifest style kept, safe identifiers | test_tovar_mods > NewBarTest (all seven tests) |
| `new` with `off`, a bad or a taken name | Refused | test_tovar_mods > NewBarTest.test_new_refuses_off_a_bad_name_or_an_existing_bar |
| `check [bars]` | Template leftovers, missing or stray profiles, missing Color, Emoji or Speaks, empty moods, repeated characters, TODO lines and unlisted bars flagged; no names checks every bar; unknown bar fails | test_tovar_mods > CheckBarTest (all nine tests); CheckMoreTest.test_check_flags_a_character_in_two_moods, CheckMoreTest.test_check_flags_a_profile_still_holding_the_todo_line (added) |
| `check` with no bars, or without `claude` on the path | Says so and fails | test_tovar_mods > ScriptUsageTest.test_check_with_no_bars_says_so, CheckMoreTest.test_check_without_claude_on_the_path_says_the_plugin_checks_did_not_run (added) |
| `check` runs the plugin checker and tests | Their failures fail the check | Covered by running `python3 tools/tovar-mods.py check` on the real repo (see the commands at the top) |
| `register <plugin> <description>` | Listed once; name without `tovar-` and folder without a manifest refused | test_tovar_mods > RegisterPluginTest (all three tests) |
| `overlap <bar> <theme>` | Verbs equal to a thinking action (own or generic) or naming a character flagged; unknown bar or theme fails; quoted brackets parsed | test_tovar_mods > OverlapTest (all six tests), RosterParsingTest.test_a_bracket_inside_a_quoted_thinking_action_does_not_cut_the_list |
| No command, unknown command, wrong arguments | Usage printed, non-zero exit | test_tovar_mods > ScriptUsageTest.test_no_command_or_an_unknown_one_prints_the_usage, ScriptUsageTest.test_each_command_explains_wrong_arguments (added) |

## Repo rules

| Rule | Tests |
|---|---|
| No em or en dashes in any tracked file | test_names > NamesTest.test_no_long_dashes; test_tovar_skills > SkillsTest.test_no_em_or_en_dashes |
| No leftover old plugin name in text or paths | test_names > NamesTest.test_no_old_name_in_text, NamesTest.test_no_old_name_in_paths |
| Every plugin and project skill starts with `tovar-` | test_names > NamesTest.test_plugins_start_with_prefix, NamesTest.test_project_skills_start_with_prefix |
| Manifests and marketplace valid | `claude plugin validate .` |
