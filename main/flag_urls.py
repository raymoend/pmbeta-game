from django.urls import path, re_path
from .flag_views import flags_near, flags_list, place_flag, flag_detail, attack_flag, capture_flag, collect_revenue, update_flag, delete_flag

urlpatterns = [
    # New canonical list endpoint expected by frontend
    path("flags/", flags_list, name="flags_list"),
    
    # Nearby alias (accepts optional lat/lon)
    path("flags/near/", flags_near, name="flags_near"),
    
    # Place
    path("flags/place/", place_flag, name="place_flag"),
    
    # Detail and actions
    re_path(r"^flags/(?P<flag_id>[^/]+)/$", flag_detail, name="flag_detail"),
    re_path(r"^flags/(?P<flag_id>[^/]+)/attack/$", attack_flag, name="attack_flag"),
    re_path(r"^flags/(?P<flag_id>[^/]+)/capture/$", capture_flag, name="capture_flag"),
    re_path(r"^flags/(?P<flag_id>[^/]+)/collect/$", collect_revenue, name="collect_flag_revenue"),
    re_path(r"^flags/(?P<flag_id>[^/]+)/update/$", update_flag, name="update_flag"),
    re_path(r"^flags/(?P<flag_id>[^/]+)/delete/$", delete_flag, name="delete_flag"),

    # PK-style run endpoints removed (FlagRun deprecated)
]

