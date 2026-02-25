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

.PHONY: feeds_lamarzocco
feeds_lamarzocco: ## Generate RSS feed for La Marzocco Blog
	$(call check_venv)
	$(call print_info,Generating La Marzocco Blog feed)
	$(Q)python feed_generators/lamarzocco_blog.py
	$(call print_success,La Marzocco Blog feed generated)

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
