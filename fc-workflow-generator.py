import json
from datetime import datetime

# Common placeholders shared across all subtypes
COMMON_PLACEHOLDERS = {
    "[[system.rejected.location.ref]]": "AUTO::system.rejected.location",
    "[[inventory.catalogue.ref]]": "AUTO::inventory.catalogue",
    "[[inventory.retailer.id]]": "AUTO::retailer",
    "[[carrier.ref]]": "AUTO::carrier",
    "[[label.url]]": "AUTO::label.url"
}

# Dynamically generate placeholders specific to each subtype
def get_autofill(subtype: str):
    dynamic = {
        f"[[workflow:order:{subtype}:network.ref]]": f"AUTO::{subtype}::network",
        f"[[workflow:order:{subtype}:virtual.catalogue.ref]]": f"AUTO::{subtype}::virtual.catalogue"
    }
    return {**COMMON_PLACEHOLDERS, **dynamic}

# Metadata builder for the workflow JSON
def generate_metadata(name: str, subtype: str, description: str, created_by="AgentAI", version="1.0"):
    return {
        "retailerId": "[[retailer.id]]",
        "version": version,
        "entityType": "ORDER",
        "entitySubtype": subtype,
        "description": description,
        "versionComment": "Generated by AI agent",
        "createdBy": created_by,
        "createdOn": datetime.utcnow().isoformat() + "+00:00",
        "id": None,
        "name": name,
    }

# Ruleset definitions per subtype
def cc_rules():
    return [
        {
            "name": "CREATE",
            "description": "Set RECEIVED, trigger ValidatePickupLocation",
            "type": "ORDER",
            "eventType": "NORMAL",
            "rules": [
                {"name": "[[account.id]].core.SetState", "props": {"status": "RECEIVED"}},
                {"name": "[[account.id]].core.SendEvent", "props": {"eventName": "ValidatePickupLocation"}}
            ],
            "triggers": [{"status": "CREATED"}],
            "userActions": []
        },
        {
            "name": "ValidatePickupLocation",
            "description": "Set BOOKED, trigger ProcessOrder",
            "type": "ORDER",
            "eventType": "NORMAL",
            "rules": [
                {"name": "[[account.id]].core.SetState", "props": {"status": "BOOKED"}},
                {"name": "[[account.id]].core.SendEvent", "props": {"eventName": "ProcessOrder"}}
            ],
            "triggers": [{"status": "RECEIVED"}],
            "userActions": []
        }
    ]

def hd_rules():
    return [
        {
            "name": "CREATE",
            "description": "Set RECEIVED, trigger ValidateDeliveryLocation",
            "type": "ORDER",
            "eventType": "NORMAL",
            "rules": [
                {"name": "[[account.id]].core.SetState", "props": {"status": "RECEIVED"}},
                {"name": "[[account.id]].core.SendEvent", "props": {"eventName": "ValidateDeliveryLocation"}}
            ],
            "triggers": [{"status": "CREATED"}],
            "userActions": []
        },
        {
            "name": "ValidateDeliveryLocation",
            "description": "Set VALIDATED, trigger BookCarrier",
            "type": "ORDER",
            "eventType": "NORMAL",
            "rules": [
                {"name": "[[account.id]].core.SetState", "props": {"status": "VALIDATED"}},
                {"name": "[[account.id]].core.SendEvent", "props": {"eventName": "BookCarrier"}}
            ],
            "triggers": [{"status": "RECEIVED"}],
            "userActions": []
        }
    ]

def multi_rules():
    return [
        {
            "name": "CREATE",
            "description": "Set RECEIVED, trigger EvaluateSplit",
            "type": "ORDER",
            "eventType": "NORMAL",
            "rules": [
                {"name": "[[account.id]].core.SetState", "props": {"status": "RECEIVED"}},
                {"name": "[[account.id]].core.SendEvent", "props": {"eventName": "EvaluateSplit"}}
            ],
            "triggers": [{"status": "CREATED"}],
            "userActions": []
        },
        {
            "name": "EvaluateSplit",
            "description": "Set SPLIT_READY, trigger ProcessSplits",
            "type": "ORDER",
            "eventType": "NORMAL",
            "rules": [
                {"name": "[[account.id]].core.SetState", "props": {"status": "SPLIT_READY"}},
                {"name": "[[account.id]].core.SendEvent", "props": {"eventName": "ProcessSplits"}}
            ],
            "triggers": [{"status": "RECEIVED"}],
            "userActions": []
        }
    ]

# Statuses per workflow subtype
def statuses(subtype: str):
    base = [
        {"name": "CREATED", "entityType": "ORDER", "category": "BOOKING"},
        {"name": "RECEIVED", "entityType": "ORDER", "category": "BOOKING"}
    ]
    if subtype == "cc":
        return base + [{"name": "BOOKED", "entityType": "ORDER", "category": "BOOKING"}]
    elif subtype == "hd":
        return base + [{"name": "VALIDATED", "entityType": "ORDER", "category": "BOOKING"}]
    elif subtype == "multi":
        return base + [{"name": "SPLIT_READY", "entityType": "ORDER", "category": "BOOKING"}]
    return base

# Common settings for all workflows
def settings():
    return {
        "fc.rubix.sdk.primaryEntityCache": "flush-on-mutation",
        "fc.rubix.sdk.webhook.retry.method": "preserve-event-details"
    }

# Main entrypoint to generate the workflow from prompt
def generate_workflow_from_prompt(prompt: str):
    prompt = prompt.lower()
    if "cc" in prompt or "click" in prompt:
        subtype = "cc"
        wf_name = "ORDER::CC_AGENT"
        desc = "Click & Collect workflow (generated by agent)"
        rules = cc_rules()
    elif "hd" in prompt or "home" in prompt:
        subtype = "hd"
        wf_name = "ORDER::HD_AGENT"
        desc = "Home Delivery workflow (generated by agent)"
        rules = hd_rules()
    elif "multi" in prompt:
        subtype = "multi"
        wf_name = "ORDER::MULTI_AGENT"
        desc = "Multi-fulfilment workflow (generated by agent)"
        rules = multi_rules()
    else:
        raise ValueError("Unsupported workflow type in prompt")

    workflow = generate_metadata(wf_name, subtype, desc)
    workflow["rulesets"] = rules
    workflow["statuses"] = statuses(subtype)
    workflow["settings"] = settings()

    # Add autofill key-values
    workflow.update(get_autofill(subtype))

    return workflow

# Save final workflow to a JSON file
def save_workflow_json(data: dict, filename: str):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[INFO] JSON saved to: {filename}")


# Example test run
if __name__ == "__main__":
    user_prompt = "Generate a multi-fulfilment order workflow"
    workflow = generate_workflow_from_prompt(user_prompt)
    save_workflow_json(workflow, "generated_order_workflow.json")
