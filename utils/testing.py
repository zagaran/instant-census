class MultifailureTest(object):
    def __enter__(self):
        self.failures = set()
        return self
    
    def __exit__(self, type_, value, tb):
        if tb:
            return
        assert not self.failures, "\n" + "".join("\n" + w for w in sorted(self.failures))
    
    def assertTrue(self, proposition, msg):
        if not proposition:
            self.failures.add(msg)
    
    def assertEqual(self, a, b, msg):
        if a != b:
            self.failures.add(msg)
    
    def assertResponseOkay(self, http_response, msg):
        if http_response.status_code >= 400:
            self.failures.add(msg)
    
    def assertRaisedException(self, func, exception, msg, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            if not isinstance(e, exception):
                self.failures.add(msg)

    def assertHasContent(self, response, content, msg):
        if content not in response.data:
            self.failures.add(msg)

    def assertRedirect(self, response, msg):
        if response.status_code != 302:
            self.failures.add(msg)
