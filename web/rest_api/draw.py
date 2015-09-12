from tastypie import fields, resources, exceptions, http
from tastypie.bundle import Bundle
from server import mongodb


class DrawResource(resources.Resource):
    """Resource representing the draws a user has any relation with

    This resource can be used to retrieve information about the draws you have
     access or to add/remove the draws you are linked with. (Note, the draw must
     already exist)
    All operations requires the user to be logged in
    """
    id = fields.CharField(attribute='_id', help_text="id of the favourite draw")
    type = fields.CharField(attribute='draw_type', help_text="type of the draw")
    title = fields.CharField(attribute='title',
                             help_text="Title of the draw",
                             null=True)
    is_shared = fields.BooleanField(attribute='is_shared',
                                    default=False,
                                    help_text="Whether the draw is public or not")
    owner = fields.CharField(attribute='owner',
                             null=True,
                             help_text="Owner of the draw")

    class Meta:
        resource_name = 'draw'
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get', 'delete']

    @property
    def _client(self):
        return mongodb.MongoDriver.instance()

    def dehydrate(self, bundle):
        bundle.data["users"] = bundle.obj.users
        return bundle

    def detail_uri_kwargs(self, bundle_or_obj):
        if isinstance(bundle_or_obj, Bundle):
            return {'pk': bundle_or_obj.obj.pk}
        else:
            return {'pk': bundle_or_obj.pk}

    def get_object_list(self, request):
        result = []
        if request.user.is_authenticated():
            draws = self._client.get_draws_with_filter({
                '$or': [
                    {'owner': request.user.pk},
                    {'users': request.user.pk},
                ]
            })
            result.extend(draws)
        return result

    def obj_get_list(self, bundle, **kwargs):
        # Filtering disabled for the moment
        return self.get_object_list(bundle.request)

    def obj_get(self, bundle, **kwargs):
        return self._client.retrieve_draw(kwargs['pk'])

    def obj_create(self, bundle, **kwargs):
        print bundle
        if not bundle.request.user.is_authenticated():
            self.unauthorized_result(None)
        if 'id' not in bundle.data:
            raise exceptions.ImmediateHttpResponse(
                response=http.HttpBadRequest("Provide an 'id' to subscribe"))
        draw_id = bundle.data['id']
        draw = self._client.retrieve_draw(draw_id)
        if bundle.request.user.pk not in draw.users:
            draw.users.append(bundle.request.user.pk)
            self._client.save_draw(draw)
        bundle.obj = draw
        return bundle

    def obj_delete(self, bundle, **kwargs):
        if not bundle.request.user.is_authenticated():
            self.unauthorized_result(None)
        draw_id = kwargs['pk']
        draw = self._client.retrieve_draw(draw_id)
        if bundle.request.user.pk in draw.users:
            draw.users.remove(bundle.request.user.pk)
            self._client.save_draw(draw)
        elif bundle.request.user.pk == draw.owner:
            draw.owner = None
            self._client.save_draw(draw)

    def rollback(self, bundles):
        pass