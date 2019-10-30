export GCOV_CC := $(shell pwd)/gcov-gcc
export GCOV_CXX := $(shell pwd)/gcov-g++

help :
	@echo "Service Builder"
	@echo "  all:           Builds all services"
	@echo "  list:          List all services"
	@echo "  <SERVICE>:     Builds single service and dependencies"

Q := @
VIRT_SERVICES :=
SUB_SERVICES :=

define virt_service
VIRT_SERVICES += $(1)
SUB_SERVICES += $($(1)_provides)
$($(1)_provides) :
	$(Q) $(MAKE) -C $(1) $$@

.PHONY: $($(1)_provides)

endef

-include $(wildcard */*.mk)

SERVICES := $(filter-out $(VIRT_SERVICES),$(patsubst %/., %, $(wildcard */.)))
.SECONDEXPANSION:

all: $(SERVICES) $(SUB_SERVICES)

$(SERVICES): $$($$@_depends)
	$(Q)$(MAKE) -C $@

list:
	$(Q)$(foreach s, $(SERVICES), echo $(s);)
	$(Q)$(foreach s, $(SUB_SERVICES), echo $(s);)

clean:
	$(Q)$(foreach s, $(SERVICES), $(MAKE) -C $(s) clean;)
	$(Q)$(foreach s, $(VIRT_SERVICES), $(MAKE) -C $(s) clean;)

mrpropper:
	$(Q)$(foreach s, $(SERVICES), $(MAKE) -C $(s) mrpropper;)
	$(Q)$(foreach s, $(VIRT_SERVICES), $(MAKE) -C $(s) mrpropper;)

.PHONY: $(SERVICES)
