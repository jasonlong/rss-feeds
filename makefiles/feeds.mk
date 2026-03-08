##########################
### RSS Feed Generation ##
##########################

.PHONY: feeds_generate_all
feeds_generate_all: ## Generate all RSS feeds
	$(call check_venv)
	$(call print_info_section,Generating all RSS feeds)
	$(Q)python feed_generators/run_all_feeds.py
	$(call print_success,All feeds generated)

.PHONY: feeds_acmeweather
feeds_acmeweather: ## Generate RSS feed for Acme Weather Blog
	$(call check_venv)
	$(call print_info,Generating Acme Weather Blog feed)
	$(Q)python feed_generators/acmeweather_blog.py
	$(call print_success,Acme Weather Blog feed generated)

.PHONY: feeds_athletic_formula1
feeds_athletic_formula1: ## Generate RSS feed for The Athletic Formula 1
	$(call check_venv)
	$(call print_info,Generating The Athletic Formula 1 feed)
	$(Q)python feed_generators/athletic_formula1_blog.py
	$(call print_success,The Athletic Formula 1 feed generated)

.PHONY: feeds_athletic_ohio_state
feeds_athletic_ohio_state: ## Generate RSS feed for The Athletic Ohio State Buckeyes
	$(call check_venv)
	$(call print_info,Generating The Athletic Ohio State Buckeyes feed)
	$(Q)python feed_generators/athletic_ohio_state_blog.py
	$(call print_success,The Athletic Ohio State Buckeyes feed generated)

.PHONY: feeds_athletic_steelers
feeds_athletic_steelers: ## Generate RSS feed for The Athletic Pittsburgh Steelers
	$(call check_venv)
	$(call print_info,Generating The Athletic Pittsburgh Steelers feed)
	$(Q)python feed_generators/athletic_steelers_blog.py
	$(call print_success,The Athletic Pittsburgh Steelers feed generated)

.PHONY: feeds_every_to
feeds_every_to: ## Generate RSS feed for Every
	$(call check_venv)
	$(call print_info,Generating Every feed)
	$(Q)python feed_generators/every_to_blog.py
	$(call print_success,Every feed generated)

.PHONY: feeds_creativeapplications
feeds_creativeapplications: ## Generate RSS feed for Creative Applications Network
	$(call check_venv)
	$(call print_info,Generating Creative Applications Network feed)
	$(Q)python feed_generators/creativeapplications_blog.py
	$(call print_success,Creative Applications Network feed generated)

.PHONY: feeds_lamarzocco
feeds_lamarzocco: ## Generate RSS feed for La Marzocco Blog
	$(call check_venv)
	$(call print_info,Generating La Marzocco Blog feed)
	$(Q)python feed_generators/lamarzocco_blog.py
	$(call print_success,La Marzocco Blog feed generated)

.PHONY: feeds_shuding
feeds_shuding: ## Generate RSS feed for Shu Ding's blog
	$(call check_venv)
	$(call print_info,Generating Shu Ding feed)
	$(Q)python feed_generators/shuding_blog.py
	$(call print_success,Shu Ding feed generated)

.PHONY: feeds_tomsachs
feeds_tomsachs: ## Generate RSS feed for Tom Sachs Store
	$(call check_venv)
	$(call print_info,Generating Tom Sachs Store feed)
	$(Q)python feed_generators/tomsachs_store.py
	$(call print_success,Tom Sachs Store feed generated)

.PHONY: clean_feeds
clean_feeds: ## Clean generated RSS feed files
	$(call print_warning,Removing generated RSS feeds)
	$(Q)rm -rf feeds/*.xml
	$(call print_success,RSS feeds removed)
