(function (global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined' ? factory(exports) :
  typeof define === 'function' && define.amd ? define(['exports'], factory) :
  (global = typeof globalThis !== 'undefined' ? globalThis : global || self, factory(global.BpmnAutoLayout = {}));
})(this, (function (exports) { 'use strict';

  /**
   * Flatten array, one level deep.
   *
   * @template T
   *
   * @param {T[][] | T[] | null} [arr]
   *
   * @return {T[]}
   */

  const nativeToString = Object.prototype.toString;
  const nativeHasOwnProperty = Object.prototype.hasOwnProperty;

  function isUndefined$1(obj) {
    return obj === undefined;
  }

  function isDefined(obj) {
    return obj !== undefined;
  }

  function isNil(obj) {
    return obj == null;
  }

  function isArray(obj) {
    return nativeToString.call(obj) === '[object Array]';
  }

  function isObject(obj) {
    return nativeToString.call(obj) === '[object Object]';
  }

  /**
   * @param {any} obj
   *
   * @return {boolean}
   */
  function isFunction(obj) {
    const tag = nativeToString.call(obj);

    return (
      tag === '[object Function]' ||
      tag === '[object AsyncFunction]' ||
      tag === '[object GeneratorFunction]' ||
      tag === '[object AsyncGeneratorFunction]' ||
      tag === '[object Proxy]'
    );
  }

  function isString(obj) {
    return nativeToString.call(obj) === '[object String]';
  }

  /**
   * Return true, if target owns a property with the given key.
   *
   * @param {Object} target
   * @param {String} key
   *
   * @return {Boolean}
   */
  function has(target, key) {
    return nativeHasOwnProperty.call(target, key);
  }

  /**
   * @template T
   * @typedef { (
   *   ((e: T) => boolean) |
   *   ((e: T, idx: number) => boolean) |
   *   ((e: T, key: string) => boolean) |
   *   string |
   *   number
   * ) } Matcher
   */

  /**
   * @template T
   * @template U
   *
   * @typedef { (
   *   ((e: T) => U) | string | number
   * ) } Extractor
   */


  /**
   * @template T
   * @typedef { (val: T, key: any) => boolean } MatchFn
   */

  /**
   * @template T
   * @typedef { T[] } ArrayCollection
   */

  /**
   * @template T
   * @typedef { { [key: string]: T } } StringKeyValueCollection
   */

  /**
   * @template T
   * @typedef { { [key: number]: T } } NumberKeyValueCollection
   */

  /**
   * @template T
   * @typedef { StringKeyValueCollection<T> | NumberKeyValueCollection<T> } KeyValueCollection
   */

  /**
   * @template T
   * @typedef { KeyValueCollection<T> | ArrayCollection<T> } Collection
   */

  /**
   * Find element in collection.
   *
   * @template T
   * @param {Collection<T>} collection
   * @param {Matcher<T>} matcher
   *
   * @return {Object}
   */
  function find(collection, matcher) {

    const matchFn = toMatcher(matcher);

    let match;

    forEach(collection, function(val, key) {
      if (matchFn(val, key)) {
        match = val;

        return false;
      }
    });

    return match;

  }


  /**
   * Find element index in collection.
   *
   * @template T
   * @param {Collection<T>} collection
   * @param {Matcher<T>} matcher
   *
   * @return {number}
   */
  function findIndex(collection, matcher) {

    const matchFn = toMatcher(matcher);

    let idx = isArray(collection) ? -1 : undefined;

    forEach(collection, function(val, key) {
      if (matchFn(val, key)) {
        idx = key;

        return false;
      }
    });

    return idx;
  }


  /**
   * Filter elements in collection.
   *
   * @template T
   * @param {Collection<T>} collection
   * @param {Matcher<T>} matcher
   *
   * @return {T[]} result
   */
  function filter(collection, matcher) {

    const matchFn = toMatcher(matcher);

    let result = [];

    forEach(collection, function(val, key) {
      if (matchFn(val, key)) {
        result.push(val);
      }
    });

    return result;
  }


  /**
   * Iterate over collection; returning something
   * (non-undefined) will stop iteration.
   *
   * @template T
   * @param {Collection<T>} collection
   * @param { ((item: T, idx: number) => (boolean|void)) | ((item: T, key: string) => (boolean|void)) } iterator
   *
   * @return {T} return result that stopped the iteration
   */
  function forEach(collection, iterator) {

    let val,
        result;

    if (isUndefined$1(collection)) {
      return;
    }

    const convertKey = isArray(collection) ? toNum : identity;

    for (let key in collection) {

      if (has(collection, key)) {
        val = collection[key];

        result = iterator(val, convertKey(key));

        if (result === false) {
          return val;
        }
      }
    }
  }


  /**
   * Transform a collection into another collection
   * by piping each member through the given fn.
   *
   * @param  {Object|Array}   collection
   * @param  {Function} fn
   *
   * @return {Array} transformed collection
   */
  function map(collection, fn) {

    let result = [];

    forEach(collection, function(val, key) {
      result.push(fn(val, key));
    });

    return result;
  }


  /**
   * @template T
   * @param {Matcher<T>} matcher
   *
   * @return {MatchFn<T>}
   */
  function toMatcher(matcher) {
    return isFunction(matcher) ? matcher : (e) => {
      return e === matcher;
    };
  }


  function identity(arg) {
    return arg;
  }

  function toNum(arg) {
    return Number(arg);
  }

  /**
   * Bind function against target <this>.
   *
   * @param  {Function} fn
   * @param  {Object}   target
   *
   * @return {Function} bound function
   */
  function bind(fn, target) {
    return fn.bind(target);
  }

  /**
   * Convenience wrapper for `Object.assign`.
   *
   * @param {Object} target
   * @param {...Object} others
   *
   * @return {Object} the target
   */
  function assign(target, ...others) {
    return Object.assign(target, ...others);
  }

  /**
   * Sets a nested property of a given object to the specified value.
   *
   * This mutates the object and returns it.
   *
   * @template T
   *
   * @param {T} target The target of the set operation.
   * @param {(string|number)[]} path The path to the nested value.
   * @param {any} value The value to set.
   *
   * @return {T}
   */
  function set(target, path, value) {

    let currentTarget = target;

    forEach(path, function(key, idx) {

      if (typeof key !== 'number' && typeof key !== 'string') {
        throw new Error('illegal key type: ' + typeof key + '. Key should be of type number or string.');
      }

      if (key === 'constructor') {
        throw new Error('illegal key: constructor');
      }

      if (key === '__proto__') {
        throw new Error('illegal key: __proto__');
      }

      let nextKey = path[idx + 1];
      let nextTarget = currentTarget[key];

      if (isDefined(nextKey) && isNil(nextTarget)) {
        nextTarget = currentTarget[key] = isNaN(+nextKey) ? {} : [];
      }

      if (isUndefined$1(nextKey)) {
        if (isUndefined$1(value)) {
          delete currentTarget[key];
        } else {
          currentTarget[key] = value;
        }
      } else {
        currentTarget = nextTarget;
      }
    });

    return target;
  }

  /**
   * Pick properties from the given target.
   *
   * @template T
   * @template {any[]} V
   *
   * @param {T} target
   * @param {V} properties
   *
   * @return Pick<T, V>
   */
  function pick(target, properties) {

    let result = {};

    let obj = Object(target);

    forEach(properties, function(prop) {

      if (prop in obj) {
        result[prop] = target[prop];
      }
    });

    return result;
  }

  /**
   * Moddle base element.
   */
  function Base() { }

  Base.prototype.get = function(name) {
    return this.$model.properties.get(this, name);
  };

  Base.prototype.set = function(name, value) {
    this.$model.properties.set(this, name, value);
  };

  /**
   * A model element factory.
   *
   * @param {Moddle} model
   * @param {Properties} properties
   */
  function Factory(model, properties) {
    this.model = model;
    this.properties = properties;
  }


  Factory.prototype.createType = function(descriptor) {

    var model = this.model;

    var props = this.properties,
        prototype = Object.create(Base.prototype);

    // initialize default values
    forEach(descriptor.properties, function(p) {
      if (!p.isMany && p.default !== undefined) {
        prototype[p.name] = p.default;
      }
    });

    props.defineModel(prototype, model);
    props.defineDescriptor(prototype, descriptor);

    var name = descriptor.ns.name;

    /**
     * The new type constructor
     */
    function ModdleElement(attrs) {
      props.define(this, '$type', { value: name, enumerable: true });
      props.define(this, '$attrs', { value: {} });
      props.define(this, '$parent', { writable: true });

      forEach(attrs, bind(function(val, key) {
        this.set(key, val);
      }, this));
    }

    ModdleElement.prototype = prototype;

    ModdleElement.hasType = prototype.$instanceOf = this.model.hasType;

    // static links
    props.defineModel(ModdleElement, model);
    props.defineDescriptor(ModdleElement, descriptor);

    return ModdleElement;
  };

  /**
   * Built-in moddle types
   */
  var BUILTINS = {
    String: true,
    Boolean: true,
    Integer: true,
    Real: true,
    Element: true
  };

  /**
   * Converters for built in types from string representations
   */
  var TYPE_CONVERTERS = {
    String: function(s) { return s; },
    Boolean: function(s) { return s === 'true'; },
    Integer: function(s) { return parseInt(s, 10); },
    Real: function(s) { return parseFloat(s); }
  };

  /**
   * Convert a type to its real representation
   */
  function coerceType(type, value) {

    var converter = TYPE_CONVERTERS[type];

    if (converter) {
      return converter(value);
    } else {
      return value;
    }
  }

  /**
   * Return whether the given type is built-in
   */
  function isBuiltIn(type) {
    return !!BUILTINS[type];
  }

  /**
   * Return whether the given type is simple
   */
  function isSimple(type) {
    return !!TYPE_CONVERTERS[type];
  }

  /**
   * Parses a namespaced attribute name of the form (ns:)localName to an object,
   * given a default prefix to assume in case no explicit namespace is given.
   *
   * @param {String} name
   * @param {String} [defaultPrefix] the default prefix to take, if none is present.
   *
   * @return {Object} the parsed name
   */
  function parseName(name, defaultPrefix) {
    var parts = name.split(/:/),
        localName, prefix;

    // no prefix (i.e. only local name)
    if (parts.length === 1) {
      localName = name;
      prefix = defaultPrefix;
    }

    // prefix + local name
    else if (parts.length === 2) {
      localName = parts[1];
      prefix = parts[0];
    }

    else {
      throw new Error('expected <prefix:localName> or <localName>, got ' + name);
    }

    name = (prefix ? prefix + ':' : '') + localName;

    return {
      name: name,
      prefix: prefix,
      localName: localName
    };
  }

  /**
   * A utility to build element descriptors.
   */
  function DescriptorBuilder(nameNs) {
    this.ns = nameNs;
    this.name = nameNs.name;
    this.allTypes = [];
    this.allTypesByName = {};
    this.properties = [];
    this.propertiesByName = {};
  }


  DescriptorBuilder.prototype.build = function() {
    return pick(this, [
      'ns',
      'name',
      'allTypes',
      'allTypesByName',
      'properties',
      'propertiesByName',
      'bodyProperty',
      'idProperty'
    ]);
  };

  /**
   * Add property at given index.
   *
   * @param {Object} p
   * @param {Number} [idx]
   * @param {Boolean} [validate=true]
   */
  DescriptorBuilder.prototype.addProperty = function(p, idx, validate) {

    if (typeof idx === 'boolean') {
      validate = idx;
      idx = undefined;
    }

    this.addNamedProperty(p, validate !== false);

    var properties = this.properties;

    if (idx !== undefined) {
      properties.splice(idx, 0, p);
    } else {
      properties.push(p);
    }
  };


  DescriptorBuilder.prototype.replaceProperty = function(oldProperty, newProperty, replace) {
    var oldNameNs = oldProperty.ns;

    var props = this.properties,
        propertiesByName = this.propertiesByName,
        rename = oldProperty.name !== newProperty.name;

    if (oldProperty.isId) {
      if (!newProperty.isId) {
        throw new Error(
          'property <' + newProperty.ns.name + '> must be id property ' +
          'to refine <' + oldProperty.ns.name + '>');
      }

      this.setIdProperty(newProperty, false);
    }

    if (oldProperty.isBody) {

      if (!newProperty.isBody) {
        throw new Error(
          'property <' + newProperty.ns.name + '> must be body property ' +
          'to refine <' + oldProperty.ns.name + '>');
      }

      // TODO: Check compatibility
      this.setBodyProperty(newProperty, false);
    }

    // validate existence and get location of old property
    var idx = props.indexOf(oldProperty);
    if (idx === -1) {
      throw new Error('property <' + oldNameNs.name + '> not found in property list');
    }

    // remove old property
    props.splice(idx, 1);

    // replacing the named property is intentional
    //
    //  * validate only if this is a "rename" operation
    //  * add at specific index unless we "replace"
    //
    this.addProperty(newProperty, replace ? undefined : idx, rename);

    // make new property available under old name
    propertiesByName[oldNameNs.name] = propertiesByName[oldNameNs.localName] = newProperty;
  };


  DescriptorBuilder.prototype.redefineProperty = function(p, targetPropertyName, replace) {

    var nsPrefix = p.ns.prefix;
    var parts = targetPropertyName.split('#');

    var name = parseName(parts[0], nsPrefix);
    var attrName = parseName(parts[1], name.prefix).name;

    var redefinedProperty = this.propertiesByName[attrName];
    if (!redefinedProperty) {
      throw new Error('refined property <' + attrName + '> not found');
    } else {
      this.replaceProperty(redefinedProperty, p, replace);
    }

    delete p.redefines;
  };

  DescriptorBuilder.prototype.addNamedProperty = function(p, validate) {
    var ns = p.ns,
        propsByName = this.propertiesByName;

    if (validate) {
      this.assertNotDefined(p, ns.name);
      this.assertNotDefined(p, ns.localName);
    }

    propsByName[ns.name] = propsByName[ns.localName] = p;
  };

  DescriptorBuilder.prototype.removeNamedProperty = function(p) {
    var ns = p.ns,
        propsByName = this.propertiesByName;

    delete propsByName[ns.name];
    delete propsByName[ns.localName];
  };

  DescriptorBuilder.prototype.setBodyProperty = function(p, validate) {

    if (validate && this.bodyProperty) {
      throw new Error(
        'body property defined multiple times ' +
        '(<' + this.bodyProperty.ns.name + '>, <' + p.ns.name + '>)');
    }

    this.bodyProperty = p;
  };

  DescriptorBuilder.prototype.setIdProperty = function(p, validate) {

    if (validate && this.idProperty) {
      throw new Error(
        'id property defined multiple times ' +
        '(<' + this.idProperty.ns.name + '>, <' + p.ns.name + '>)');
    }

    this.idProperty = p;
  };

  DescriptorBuilder.prototype.assertNotTrait = function(typeDescriptor) {

    const _extends = typeDescriptor.extends || [];

    if (_extends.length) {
      throw new Error(
        `cannot create <${ typeDescriptor.name }> extending <${ typeDescriptor.extends }>`
      );
    }
  };

  DescriptorBuilder.prototype.assertNotDefined = function(p, name) {
    var propertyName = p.name,
        definedProperty = this.propertiesByName[propertyName];

    if (definedProperty) {
      throw new Error(
        'property <' + propertyName + '> already defined; ' +
        'override of <' + definedProperty.definedBy.ns.name + '#' + definedProperty.ns.name + '> by ' +
        '<' + p.definedBy.ns.name + '#' + p.ns.name + '> not allowed without redefines');
    }
  };

  DescriptorBuilder.prototype.hasProperty = function(name) {
    return this.propertiesByName[name];
  };

  DescriptorBuilder.prototype.addTrait = function(t, inherited) {

    if (inherited) {
      this.assertNotTrait(t);
    }

    var typesByName = this.allTypesByName,
        types = this.allTypes;

    var typeName = t.name;

    if (typeName in typesByName) {
      return;
    }

    forEach(t.properties, bind(function(p) {

      // clone property to allow extensions
      p = assign({}, p, {
        name: p.ns.localName,
        inherited: inherited
      });

      Object.defineProperty(p, 'definedBy', {
        value: t
      });

      var replaces = p.replaces,
          redefines = p.redefines;

      // add replace/redefine support
      if (replaces || redefines) {
        this.redefineProperty(p, replaces || redefines, replaces);
      } else {
        if (p.isBody) {
          this.setBodyProperty(p);
        }
        if (p.isId) {
          this.setIdProperty(p);
        }
        this.addProperty(p);
      }
    }, this));

    types.push(t);
    typesByName[typeName] = t;
  };

  /**
   * A registry of Moddle packages.
   *
   * @param {Array<Package>} packages
   * @param {Properties} properties
   */
  function Registry(packages, properties) {
    this.packageMap = {};
    this.typeMap = {};

    this.packages = [];

    this.properties = properties;

    forEach(packages, bind(this.registerPackage, this));
  }


  Registry.prototype.getPackage = function(uriOrPrefix) {
    return this.packageMap[uriOrPrefix];
  };

  Registry.prototype.getPackages = function() {
    return this.packages;
  };


  Registry.prototype.registerPackage = function(pkg) {

    // copy package
    pkg = assign({}, pkg);

    var pkgMap = this.packageMap;

    ensureAvailable(pkgMap, pkg, 'prefix');
    ensureAvailable(pkgMap, pkg, 'uri');

    // register types
    forEach(pkg.types, bind(function(descriptor) {
      this.registerType(descriptor, pkg);
    }, this));

    pkgMap[pkg.uri] = pkgMap[pkg.prefix] = pkg;
    this.packages.push(pkg);
  };


  /**
   * Register a type from a specific package with us
   */
  Registry.prototype.registerType = function(type, pkg) {

    type = assign({}, type, {
      superClass: (type.superClass || []).slice(),
      extends: (type.extends || []).slice(),
      properties: (type.properties || []).slice(),
      meta: assign((type.meta || {}))
    });

    var ns = parseName(type.name, pkg.prefix),
        name = ns.name,
        propertiesByName = {};

    // parse properties
    forEach(type.properties, bind(function(p) {

      // namespace property names
      var propertyNs = parseName(p.name, ns.prefix),
          propertyName = propertyNs.name;

      // namespace property types
      if (!isBuiltIn(p.type)) {
        p.type = parseName(p.type, propertyNs.prefix).name;
      }

      assign(p, {
        ns: propertyNs,
        name: propertyName
      });

      propertiesByName[propertyName] = p;
    }, this));

    // update ns + name
    assign(type, {
      ns: ns,
      name: name,
      propertiesByName: propertiesByName
    });

    forEach(type.extends, bind(function(extendsName) {
      var extendsNameNs = parseName(extendsName, ns.prefix);

      var extended = this.typeMap[extendsNameNs.name];

      extended.traits = extended.traits || [];
      extended.traits.push(name);
    }, this));

    // link to package
    this.definePackage(type, pkg);

    // register
    this.typeMap[name] = type;
  };


  /**
   * Traverse the type hierarchy from bottom to top,
   * calling iterator with (type, inherited) for all elements in
   * the inheritance chain.
   *
   * @param {Object} nsName
   * @param {Function} iterator
   * @param {Boolean} [trait=false]
   */
  Registry.prototype.mapTypes = function(nsName, iterator, trait) {

    var type = isBuiltIn(nsName.name) ? { name: nsName.name } : this.typeMap[nsName.name];

    var self = this;

    /**
     * Traverse the selected super type or trait
     *
     * @param {String} cls
     * @param {Boolean} [trait=false]
     */
    function traverse(cls, trait) {
      var parentNs = parseName(cls, isBuiltIn(cls) ? '' : nsName.prefix);
      self.mapTypes(parentNs, iterator, trait);
    }

    /**
     * Traverse the selected trait.
     *
     * @param {String} cls
     */
    function traverseTrait(cls) {
      return traverse(cls, true);
    }

    /**
     * Traverse the selected super type
     *
     * @param {String} cls
     */
    function traverseSuper(cls) {
      return traverse(cls, false);
    }

    if (!type) {
      throw new Error('unknown type <' + nsName.name + '>');
    }

    forEach(type.superClass, trait ? traverseTrait : traverseSuper);

    // call iterator with (type, inherited=!trait)
    iterator(type, !trait);

    forEach(type.traits, traverseTrait);
  };


  /**
   * Returns the effective descriptor for a type.
   *
   * @param  {String} type the namespaced name (ns:localName) of the type
   *
   * @return {Descriptor} the resulting effective descriptor
   */
  Registry.prototype.getEffectiveDescriptor = function(name) {

    var nsName = parseName(name);

    var builder = new DescriptorBuilder(nsName);

    this.mapTypes(nsName, function(type, inherited) {
      builder.addTrait(type, inherited);
    });

    var descriptor = builder.build();

    // define package link
    this.definePackage(descriptor, descriptor.allTypes[descriptor.allTypes.length - 1].$pkg);

    return descriptor;
  };


  Registry.prototype.definePackage = function(target, pkg) {
    this.properties.define(target, '$pkg', { value: pkg });
  };



  // helpers ////////////////////////////

  function ensureAvailable(packageMap, pkg, identifierKey) {

    var value = pkg[identifierKey];

    if (value in packageMap) {
      throw new Error('package with ' + identifierKey + ' <' + value + '> already defined');
    }
  }

  /**
   * A utility that gets and sets properties of model elements.
   *
   * @param {Model} model
   */
  function Properties(model) {
    this.model = model;
  }


  /**
   * Sets a named property on the target element.
   * If the value is undefined, the property gets deleted.
   *
   * @param {Object} target
   * @param {String} name
   * @param {Object} value
   */
  Properties.prototype.set = function(target, name, value) {

    if (!isString(name) || !name.length) {
      throw new TypeError('property name must be a non-empty string');
    }

    var property = this.getProperty(target, name);

    var propertyName = property && property.name;

    if (isUndefined(value)) {

      // unset the property, if the specified value is undefined;
      // delete from $attrs (for extensions) or the target itself
      if (property) {
        delete target[propertyName];
      } else {
        delete target.$attrs[stripGlobal(name)];
      }
    } else {

      // set the property, defining well defined properties on the fly
      // or simply updating them in target.$attrs (for extensions)
      if (property) {
        if (propertyName in target) {
          target[propertyName] = value;
        } else {
          defineProperty(target, property, value);
        }
      } else {
        target.$attrs[stripGlobal(name)] = value;
      }
    }
  };

  /**
   * Returns the named property of the given element
   *
   * @param  {Object} target
   * @param  {String} name
   *
   * @return {Object}
   */
  Properties.prototype.get = function(target, name) {

    var property = this.getProperty(target, name);

    if (!property) {
      return target.$attrs[stripGlobal(name)];
    }

    var propertyName = property.name;

    // check if access to collection property and lazily initialize it
    if (!target[propertyName] && property.isMany) {
      defineProperty(target, property, []);
    }

    return target[propertyName];
  };


  /**
   * Define a property on the target element
   *
   * @param  {Object} target
   * @param  {String} name
   * @param  {Object} options
   */
  Properties.prototype.define = function(target, name, options) {

    if (!options.writable) {

      var value = options.value;

      // use getters for read-only variables to support ES6 proxies
      // cf. https://github.com/bpmn-io/internal-docs/issues/386
      options = assign({}, options, {
        get: function() { return value; }
      });

      delete options.value;
    }

    Object.defineProperty(target, name, options);
  };


  /**
   * Define the descriptor for an element
   */
  Properties.prototype.defineDescriptor = function(target, descriptor) {
    this.define(target, '$descriptor', { value: descriptor });
  };

  /**
   * Define the model for an element
   */
  Properties.prototype.defineModel = function(target, model) {
    this.define(target, '$model', { value: model });
  };

  /**
   * Return property with the given name on the element.
   *
   * @param {any} target
   * @param {string} name
   *
   * @return {object | null} property
   */
  Properties.prototype.getProperty = function(target, name) {

    var model = this.model;

    var property = model.getPropertyDescriptor(target, name);

    if (property) {
      return property;
    }

    if (name.includes(':')) {
      return null;
    }

    const strict = model.config.strict;

    if (typeof strict !== 'undefined') {
      const error = new TypeError(`unknown property <${ name }> on <${ target.$type }>`);

      if (strict) {
        throw error;
      } else {

        // eslint-disable-next-line no-undef
        typeof console !== 'undefined' && console.warn(error);
      }
    }

    return null;
  };

  function isUndefined(val) {
    return typeof val === 'undefined';
  }

  function defineProperty(target, property, value) {
    Object.defineProperty(target, property.name, {
      enumerable: !property.isReference,
      writable: true,
      value: value,
      configurable: true
    });
  }

  function stripGlobal(name) {
    return name.replace(/^:/, '');
  }

  // Moddle implementation /////////////////////////////////////////////////

  /**
   * @class Moddle
   *
   * A model that can be used to create elements of a specific type.
   *
   * @example
   *
   * var Moddle = require('moddle');
   *
   * var pkg = {
   *   name: 'mypackage',
   *   prefix: 'my',
   *   types: [
   *     { name: 'Root' }
   *   ]
   * };
   *
   * var moddle = new Moddle([pkg]);
   *
   * @param {Array<Package>} packages the packages to contain
   *
   * @param { { strict?: boolean } } [config] moddle configuration
   */
  function Moddle(packages, config = {}) {

    this.properties = new Properties(this);

    this.factory = new Factory(this, this.properties);
    this.registry = new Registry(packages, this.properties);

    this.typeCache = {};

    this.config = config;
  }


  /**
   * Create an instance of the specified type.
   *
   * @method Moddle#create
   *
   * @example
   *
   * var foo = moddle.create('my:Foo');
   * var bar = moddle.create('my:Bar', { id: 'BAR_1' });
   *
   * @param  {String|Object} descriptor the type descriptor or name know to the model
   * @param  {Object} attrs   a number of attributes to initialize the model instance with
   * @return {Object}         model instance
   */
  Moddle.prototype.create = function(descriptor, attrs) {
    var Type = this.getType(descriptor);

    if (!Type) {
      throw new Error('unknown type <' + descriptor + '>');
    }

    return new Type(attrs);
  };


  /**
   * Returns the type representing a given descriptor
   *
   * @method Moddle#getType
   *
   * @example
   *
   * var Foo = moddle.getType('my:Foo');
   * var foo = new Foo({ 'id' : 'FOO_1' });
   *
   * @param  {String|Object} descriptor the type descriptor or name know to the model
   * @return {Object}         the type representing the descriptor
   */
  Moddle.prototype.getType = function(descriptor) {

    var cache = this.typeCache;

    var name = isString(descriptor) ? descriptor : descriptor.ns.name;

    var type = cache[name];

    if (!type) {
      descriptor = this.registry.getEffectiveDescriptor(name);
      type = cache[name] = this.factory.createType(descriptor);
    }

    return type;
  };


  /**
   * Creates an any-element type to be used within model instances.
   *
   * This can be used to create custom elements that lie outside the meta-model.
   * The created element contains all the meta-data required to serialize it
   * as part of meta-model elements.
   *
   * @method Moddle#createAny
   *
   * @example
   *
   * var foo = moddle.createAny('vendor:Foo', 'http://vendor', {
   *   value: 'bar'
   * });
   *
   * var container = moddle.create('my:Container', 'http://my', {
   *   any: [ foo ]
   * });
   *
   * // go ahead and serialize the stuff
   *
   *
   * @param  {String} name  the name of the element
   * @param  {String} nsUri the namespace uri of the element
   * @param  {Object} [properties] a map of properties to initialize the instance with
   * @return {Object} the any type instance
   */
  Moddle.prototype.createAny = function(name, nsUri, properties) {

    var nameNs = parseName(name);

    var element = {
      $type: name,
      $instanceOf: function(type) {
        return type === this.$type;
      },
      get: function(key) {
        return this[key];
      },
      set: function(key, value) {
        set(this, [ key ], value);
      }
    };

    var descriptor = {
      name: name,
      isGeneric: true,
      ns: {
        prefix: nameNs.prefix,
        localName: nameNs.localName,
        uri: nsUri
      }
    };

    this.properties.defineDescriptor(element, descriptor);
    this.properties.defineModel(element, this);
    this.properties.define(element, 'get', { enumerable: false, writable: true });
    this.properties.define(element, 'set', { enumerable: false, writable: true });
    this.properties.define(element, '$parent', { enumerable: false, writable: true });
    this.properties.define(element, '$instanceOf', { enumerable: false, writable: true });

    forEach(properties, function(a, key) {
      if (isObject(a) && a.value !== undefined) {
        element[a.name] = a.value;
      } else {
        element[key] = a;
      }
    });

    return element;
  };

  /**
   * Returns a registered package by uri or prefix
   *
   * @return {Object} the package
   */
  Moddle.prototype.getPackage = function(uriOrPrefix) {
    return this.registry.getPackage(uriOrPrefix);
  };

  /**
   * Returns a snapshot of all known packages
   *
   * @return {Object} the package
   */
  Moddle.prototype.getPackages = function() {
    return this.registry.getPackages();
  };

  /**
   * Returns the descriptor for an element
   */
  Moddle.prototype.getElementDescriptor = function(element) {
    return element.$descriptor;
  };

  /**
   * Returns true if the given descriptor or instance
   * represents the given type.
   *
   * May be applied to this, if element is omitted.
   */
  Moddle.prototype.hasType = function(element, type) {
    if (type === undefined) {
      type = element;
      element = this;
    }

    var descriptor = element.$model.getElementDescriptor(element);

    return (type in descriptor.allTypesByName);
  };

  /**
   * Returns the descriptor of an elements named property
   */
  Moddle.prototype.getPropertyDescriptor = function(element, property) {
    return this.getElementDescriptor(element).propertiesByName[property];
  };

  /**
   * Returns a mapped type's descriptor
   */
  Moddle.prototype.getTypeDescriptor = function(type) {
    return this.registry.typeMap[type];
  };

  var fromCharCode = String.fromCharCode;

  var hasOwnProperty = Object.prototype.hasOwnProperty;

  var ENTITY_PATTERN = /&#(\d+);|&#x([0-9a-f]+);|&(\w+);/ig;

  var ENTITY_MAPPING = {
    'amp': '&',
    'apos': '\'',
    'gt': '>',
    'lt': '<',
    'quot': '"'
  };

  // map UPPERCASE variants of supported special chars
  Object.keys(ENTITY_MAPPING).forEach(function(k) {
    ENTITY_MAPPING[k.toUpperCase()] = ENTITY_MAPPING[k];
  });


  function replaceEntities(_, d, x, z) {

    // reserved names, i.e. &nbsp;
    if (z) {
      if (hasOwnProperty.call(ENTITY_MAPPING, z)) {
        return ENTITY_MAPPING[z];
      } else {

        // fall back to original value
        return '&' + z + ';';
      }
    }

    // decimal encoded char
    if (d) {
      return fromCharCode(d);
    }

    // hex encoded char
    return fromCharCode(parseInt(x, 16));
  }


  /**
   * A basic entity decoder that can decode a minimal
   * sub-set of reserved names (&amp;) as well as
   * hex (&#xaaf;) and decimal (&#1231;) encoded characters.
   *
   * @param {string} s
   *
   * @return {string} decoded string
   */
  function decodeEntities(s) {
    if (s.length > 3 && s.indexOf('&') !== -1) {
      return s.replace(ENTITY_PATTERN, replaceEntities);
    }

    return s;
  }

  var NON_WHITESPACE_OUTSIDE_ROOT_NODE = 'non-whitespace outside of root node';

  function error$1(msg) {
    return new Error(msg);
  }

  function missingNamespaceForPrefix(prefix) {
    return 'missing namespace for prefix <' + prefix + '>';
  }

  function getter(getFn) {
    return {
      'get': getFn,
      'enumerable': true
    };
  }

  function cloneNsMatrix(nsMatrix) {
    var clone = {}, key;
    for (key in nsMatrix) {
      clone[key] = nsMatrix[key];
    }
    return clone;
  }

  function uriPrefix(prefix) {
    return prefix + '$uri';
  }

  function buildNsMatrix(nsUriToPrefix) {
    var nsMatrix = {},
        uri,
        prefix;

    for (uri in nsUriToPrefix) {
      prefix = nsUriToPrefix[uri];
      nsMatrix[prefix] = prefix;
      nsMatrix[uriPrefix(prefix)] = uri;
    }

    return nsMatrix;
  }

  function noopGetContext() {
    return { line: 0, column: 0 };
  }

  function throwFunc(err) {
    throw err;
  }

  /**
   * Creates a new parser with the given options.
   *
   * @constructor
   *
   * @param  {!Object<string, ?>=} options
   */
  function Parser(options) {

    if (!this) {
      return new Parser(options);
    }

    var proxy = options && options['proxy'];

    var onText,
        onOpenTag,
        onCloseTag,
        onCDATA,
        onError = throwFunc,
        onWarning,
        onComment,
        onQuestion,
        onAttention;

    var getContext = noopGetContext;

    /**
     * Do we need to parse the current elements attributes for namespaces?
     *
     * @type {boolean}
     */
    var maybeNS = false;

    /**
     * Do we process namespaces at all?
     *
     * @type {boolean}
     */
    var isNamespace = false;

    /**
     * The caught error returned on parse end
     *
     * @type {Error}
     */
    var returnError = null;

    /**
     * Should we stop parsing?
     *
     * @type {boolean}
     */
    var parseStop = false;

    /**
     * A map of { uri: prefix } used by the parser.
     *
     * This map will ensure we can normalize prefixes during processing;
     * for each uri, only one prefix will be exposed to the handlers.
     *
     * @type {!Object<string, string>}}
     */
    var nsUriToPrefix;

    /**
     * Handle parse error.
     *
     * @param  {string|Error} err
     */
    function handleError(err) {
      if (!(err instanceof Error)) {
        err = error$1(err);
      }

      returnError = err;

      onError(err, getContext);
    }

    /**
     * Handle parse error.
     *
     * @param  {string|Error} err
     */
    function handleWarning(err) {

      if (!onWarning) {
        return;
      }

      if (!(err instanceof Error)) {
        err = error$1(err);
      }

      onWarning(err, getContext);
    }

    /**
     * Register parse listener.
     *
     * @param  {string}   name
     * @param  {Function} cb
     *
     * @return {Parser}
     */
    this['on'] = function(name, cb) {

      if (typeof cb !== 'function') {
        throw error$1('required args <name, cb>');
      }

      switch (name) {
      case 'openTag': onOpenTag = cb; break;
      case 'text': onText = cb; break;
      case 'closeTag': onCloseTag = cb; break;
      case 'error': onError = cb; break;
      case 'warn': onWarning = cb; break;
      case 'cdata': onCDATA = cb; break;
      case 'attention': onAttention = cb; break; // <!XXXXX zzzz="eeee">
      case 'question': onQuestion = cb; break; // <? ....  ?>
      case 'comment': onComment = cb; break;
      default:
        throw error$1('unsupported event: ' + name);
      }

      return this;
    };

    /**
     * Set the namespace to prefix mapping.
     *
     * @example
     *
     * parser.ns({
     *   'http://foo': 'foo',
     *   'http://bar': 'bar'
     * });
     *
     * @param  {!Object<string, string>} nsMap
     *
     * @return {Parser}
     */
    this['ns'] = function(nsMap) {

      if (typeof nsMap === 'undefined') {
        nsMap = {};
      }

      if (typeof nsMap !== 'object') {
        throw error$1('required args <nsMap={}>');
      }

      var _nsUriToPrefix = {}, k;

      for (k in nsMap) {
        _nsUriToPrefix[k] = nsMap[k];
      }

      isNamespace = true;
      nsUriToPrefix = _nsUriToPrefix;

      return this;
    };

    /**
     * Parse xml string.
     *
     * @param  {string} xml
     *
     * @return {Error} returnError, if not thrown
     */
    this['parse'] = function(xml) {
      if (typeof xml !== 'string') {
        throw error$1('required args <xml=string>');
      }

      returnError = null;

      parse(xml);

      getContext = noopGetContext;
      parseStop = false;

      return returnError;
    };

    /**
     * Stop parsing.
     */
    this['stop'] = function() {
      parseStop = true;
    };

    /**
     * Parse string, invoking configured listeners on element.
     *
     * @param  {string} xml
     */
    function parse(xml) {
      var nsMatrixStack = isNamespace ? [] : null,
          nsMatrix = isNamespace ? buildNsMatrix(nsUriToPrefix) : null,
          _nsMatrix,
          nodeStack = [],
          anonymousNsCount = 0,
          tagStart = false,
          tagEnd = false,
          i = 0, j = 0,
          x, y, q, w, v,
          xmlns,
          elementName,
          _elementName,
          elementProxy
          ;

      var attrsString = '',
          attrsStart = 0,
          cachedAttrs // false = parsed with errors, null = needs parsing
          ;

      /**
       * Parse attributes on demand and returns the parsed attributes.
       *
       * Return semantics: (1) `false` on attribute parse error,
       * (2) object hash on extracted attrs.
       *
       * @return {boolean|Object}
       */
      function getAttrs() {
        if (cachedAttrs !== null) {
          return cachedAttrs;
        }

        var nsUri,
            nsUriPrefix,
            nsName,
            defaultAlias = isNamespace && nsMatrix['xmlns'],
            attrList = isNamespace && maybeNS ? [] : null,
            i = attrsStart,
            s = attrsString,
            l = s.length,
            hasNewMatrix,
            newalias,
            value,
            alias,
            name,
            attrs = {},
            seenAttrs = {},
            skipAttr,
            w,
            j;

        parseAttr:
        for (; i < l; i++) {
          skipAttr = false;
          w = s.charCodeAt(i);

          if (w === 32 || (w < 14 && w > 8)) { // WHITESPACE={ \f\n\r\t\v}
            continue;
          }

          // wait for non whitespace character
          if (w < 65 || w > 122 || (w > 90 && w < 97)) {
            if (w !== 95 && w !== 58) { // char 95"_" 58":"
              handleWarning('illegal first char attribute name');
              skipAttr = true;
            }
          }

          // parse attribute name
          for (j = i + 1; j < l; j++) {
            w = s.charCodeAt(j);

            if (
              w > 96 && w < 123 ||
              w > 64 && w < 91 ||
              w > 47 && w < 59 ||
              w === 46 || // '.'
              w === 45 || // '-'
              w === 95 // '_'
            ) {
              continue;
            }

            // unexpected whitespace
            if (w === 32 || (w < 14 && w > 8)) { // WHITESPACE
              handleWarning('missing attribute value');
              i = j;

              continue parseAttr;
            }

            // expected "="
            if (w === 61) { // "=" == 61
              break;
            }

            handleWarning('illegal attribute name char');
            skipAttr = true;
          }

          name = s.substring(i, j);

          if (name === 'xmlns:xmlns') {
            handleWarning('illegal declaration of xmlns');
            skipAttr = true;
          }

          w = s.charCodeAt(j + 1);

          if (w === 34) { // '"'
            j = s.indexOf('"', i = j + 2);

            if (j === -1) {
              j = s.indexOf('\'', i);

              if (j !== -1) {
                handleWarning('attribute value quote missmatch');
                skipAttr = true;
              }
            }

          } else if (w === 39) { // "'"
            j = s.indexOf('\'', i = j + 2);

            if (j === -1) {
              j = s.indexOf('"', i);

              if (j !== -1) {
                handleWarning('attribute value quote missmatch');
                skipAttr = true;
              }
            }

          } else {
            handleWarning('missing attribute value quotes');
            skipAttr = true;

            // skip to next space
            for (j = j + 1; j < l; j++) {
              w = s.charCodeAt(j + 1);

              if (w === 32 || (w < 14 && w > 8)) { // WHITESPACE
                break;
              }
            }

          }

          if (j === -1) {
            handleWarning('missing closing quotes');

            j = l;
            skipAttr = true;
          }

          if (!skipAttr) {
            value = s.substring(i, j);
          }

          i = j;

          // ensure SPACE follows attribute
          // skip illegal content otherwise
          // example a="b"c
          for (; j + 1 < l; j++) {
            w = s.charCodeAt(j + 1);

            if (w === 32 || (w < 14 && w > 8)) { // WHITESPACE
              break;
            }

            // FIRST ILLEGAL CHAR
            if (i === j) {
              handleWarning('illegal character after attribute end');
              skipAttr = true;
            }
          }

          // advance cursor to next attribute
          i = j + 1;

          if (skipAttr) {
            continue parseAttr;
          }

          // check attribute re-declaration
          if (name in seenAttrs) {
            handleWarning('attribute <' + name + '> already defined');
            continue;
          }

          seenAttrs[name] = true;

          if (!isNamespace) {
            attrs[name] = value;
            continue;
          }

          // try to extract namespace information
          if (maybeNS) {
            newalias = (
              name === 'xmlns'
                ? 'xmlns'
                : (name.charCodeAt(0) === 120 && name.substr(0, 6) === 'xmlns:')
                  ? name.substr(6)
                  : null
            );

            // handle xmlns(:alias) assignment
            if (newalias !== null) {
              nsUri = decodeEntities(value);
              nsUriPrefix = uriPrefix(newalias);

              alias = nsUriToPrefix[nsUri];

              if (!alias) {

                // no prefix defined or prefix collision
                if (
                  (newalias === 'xmlns') ||
                  (nsUriPrefix in nsMatrix && nsMatrix[nsUriPrefix] !== nsUri)
                ) {

                  // alocate free ns prefix
                  do {
                    alias = 'ns' + (anonymousNsCount++);
                  } while (typeof nsMatrix[alias] !== 'undefined');
                } else {
                  alias = newalias;
                }

                nsUriToPrefix[nsUri] = alias;
              }

              if (nsMatrix[newalias] !== alias) {
                if (!hasNewMatrix) {
                  nsMatrix = cloneNsMatrix(nsMatrix);
                  hasNewMatrix = true;
                }

                nsMatrix[newalias] = alias;
                if (newalias === 'xmlns') {
                  nsMatrix[uriPrefix(alias)] = nsUri;
                  defaultAlias = alias;
                }

                nsMatrix[nsUriPrefix] = nsUri;
              }

              // expose xmlns(:asd)="..." in attributes
              attrs[name] = value;
              continue;
            }

            // collect attributes until all namespace
            // declarations are processed
            attrList.push(name, value);
            continue;

          } /** end if (maybeNs) */

          // handle attributes on element without
          // namespace declarations
          w = name.indexOf(':');
          if (w === -1) {
            attrs[name] = value;
            continue;
          }

          // normalize ns attribute name
          if (!(nsName = nsMatrix[name.substring(0, w)])) {
            handleWarning(missingNamespaceForPrefix(name.substring(0, w)));
            continue;
          }

          name = defaultAlias === nsName
            ? name.substr(w + 1)
            : nsName + name.substr(w);

          // end: normalize ns attribute name

          attrs[name] = value;
        }


        // handle deferred, possibly namespaced attributes
        if (maybeNS) {

          // normalize captured attributes
          for (i = 0, l = attrList.length; i < l; i++) {

            name = attrList[i++];
            value = attrList[i];

            w = name.indexOf(':');

            if (w !== -1) {

              // normalize ns attribute name
              if (!(nsName = nsMatrix[name.substring(0, w)])) {
                handleWarning(missingNamespaceForPrefix(name.substring(0, w)));
                continue;
              }

              name = defaultAlias === nsName
                ? name.substr(w + 1)
                : nsName + name.substr(w);

              // end: normalize ns attribute name
            }

            attrs[name] = value;
          }

          // end: normalize captured attributes
        }

        return cachedAttrs = attrs;
      }

      /**
       * Extract the parse context { line, column, part }
       * from the current parser position.
       *
       * @return {Object} parse context
       */
      function getParseContext() {
        var splitsRe = /(\r\n|\r|\n)/g;

        var line = 0;
        var column = 0;
        var startOfLine = 0;
        var endOfLine = j;
        var match;
        var data;

        while (i >= startOfLine) {

          match = splitsRe.exec(xml);

          if (!match) {
            break;
          }

          // end of line = (break idx + break chars)
          endOfLine = match[0].length + match.index;

          if (endOfLine > i) {
            break;
          }

          // advance to next line
          line += 1;

          startOfLine = endOfLine;
        }

        // EOF errors
        if (i == -1) {
          column = endOfLine;
          data = xml.substring(j);
        } else

        // start errors
        if (j === 0) {
          data = xml.substring(j, i);
        }

        // other errors
        else {
          column = i - startOfLine;
          data = (j == -1 ? xml.substring(i) : xml.substring(i, j + 1));
        }

        return {
          'data': data,
          'line': line,
          'column': column
        };
      }

      getContext = getParseContext;


      if (proxy) {
        elementProxy = Object.create({}, {
          'name': getter(function() {
            return elementName;
          }),
          'originalName': getter(function() {
            return _elementName;
          }),
          'attrs': getter(getAttrs),
          'ns': getter(function() {
            return nsMatrix;
          })
        });
      }

      // actual parse logic
      while (j !== -1) {

        if (xml.charCodeAt(j) === 60) { // "<"
          i = j;
        } else {
          i = xml.indexOf('<', j);
        }

        // parse end
        if (i === -1) {
          if (nodeStack.length) {
            return handleError('unexpected end of file');
          }

          if (j === 0) {
            return handleError('missing start tag');
          }

          if (j < xml.length) {
            if (xml.substring(j).trim()) {
              handleWarning(NON_WHITESPACE_OUTSIDE_ROOT_NODE);
            }
          }

          return;
        }

        // parse text
        if (j !== i) {

          if (nodeStack.length) {
            if (onText) {
              onText(xml.substring(j, i), decodeEntities, getContext);

              if (parseStop) {
                return;
              }
            }
          } else {
            if (xml.substring(j, i).trim()) {
              handleWarning(NON_WHITESPACE_OUTSIDE_ROOT_NODE);

              if (parseStop) {
                return;
              }
            }
          }
        }

        w = xml.charCodeAt(i + 1);

        // parse comments + CDATA
        if (w === 33) { // "!"
          q = xml.charCodeAt(i + 2);

          // CDATA section
          if (q === 91 && xml.substr(i + 3, 6) === 'CDATA[') { // 91 == "["
            j = xml.indexOf(']]>', i);
            if (j === -1) {
              return handleError('unclosed cdata');
            }

            if (onCDATA) {
              onCDATA(xml.substring(i + 9, j), getContext);
              if (parseStop) {
                return;
              }
            }

            j += 3;
            continue;
          }

          // comment
          if (q === 45 && xml.charCodeAt(i + 3) === 45) { // 45 == "-"
            j = xml.indexOf('-->', i);
            if (j === -1) {
              return handleError('unclosed comment');
            }


            if (onComment) {
              onComment(xml.substring(i + 4, j), decodeEntities, getContext);
              if (parseStop) {
                return;
              }
            }

            j += 3;
            continue;
          }
        }

        // parse question <? ... ?>
        if (w === 63) { // "?"
          j = xml.indexOf('?>', i);
          if (j === -1) {
            return handleError('unclosed question');
          }

          if (onQuestion) {
            onQuestion(xml.substring(i, j + 2), getContext);
            if (parseStop) {
              return;
            }
          }

          j += 2;
          continue;
        }

        // find matching closing tag for attention or standard tags
        // for that we must skip through attribute values
        // (enclosed in single or double quotes)
        for (x = i + 1; ; x++) {
          v = xml.charCodeAt(x);
          if (isNaN(v)) {
            j = -1;
            return handleError('unclosed tag');
          }

          // [10] AttValue ::= '"' ([^<&"] | Reference)* '"' | "'" ([^<&'] | Reference)* "'"
          // skips the quoted string
          // (double quotes) does not appear in a literal enclosed by (double quotes)
          // (single quote) does not appear in a literal enclosed by (single quote)
          if (v === 34) { //  '"'
            q = xml.indexOf('"', x + 1);
            x = q !== -1 ? q : x;
          } else if (v === 39) { // "'"
            q = xml.indexOf("'", x + 1);
            x = q !== -1 ? q : x;
          } else if (v === 62) { // '>'
            j = x;
            break;
          }
        }


        // parse attention <! ...>
        // previously comment and CDATA have already been parsed
        if (w === 33) { // "!"

          if (onAttention) {
            onAttention(xml.substring(i, j + 1), decodeEntities, getContext);
            if (parseStop) {
              return;
            }
          }

          j += 1;
          continue;
        }

        // don't process attributes;
        // there are none
        cachedAttrs = {};

        // if (xml.charCodeAt(i+1) === 47) { // </...
        if (w === 47) { // </...
          tagStart = false;
          tagEnd = true;

          if (!nodeStack.length) {
            return handleError('missing open tag');
          }

          // verify open <-> close tag match
          x = elementName = nodeStack.pop();
          q = i + 2 + x.length;

          if (xml.substring(i + 2, q) !== x) {
            return handleError('closing tag mismatch');
          }

          // verify chars in close tag
          for (; q < j; q++) {
            w = xml.charCodeAt(q);

            if (w === 32 || (w > 8 && w < 14)) { // \f\n\r\t\v space
              continue;
            }

            return handleError('close tag');
          }

        } else {
          if (xml.charCodeAt(j - 1) === 47) { // .../>
            x = elementName = xml.substring(i + 1, j - 1);

            tagStart = true;
            tagEnd = true;

          } else {
            x = elementName = xml.substring(i + 1, j);

            tagStart = true;
            tagEnd = false;
          }

          if (!(w > 96 && w < 123 || w > 64 && w < 91 || w === 95 || w === 58)) { // char 95"_" 58":"
            return handleError('illegal first char nodeName');
          }

          for (q = 1, y = x.length; q < y; q++) {
            w = x.charCodeAt(q);

            if (w > 96 && w < 123 || w > 64 && w < 91 || w > 47 && w < 59 || w === 45 || w === 95 || w == 46) {
              continue;
            }

            if (w === 32 || (w < 14 && w > 8)) { // \f\n\r\t\v space
              elementName = x.substring(0, q);

              // maybe there are attributes
              cachedAttrs = null;
              break;
            }

            return handleError('invalid nodeName');
          }

          if (!tagEnd) {
            nodeStack.push(elementName);
          }
        }

        if (isNamespace) {

          _nsMatrix = nsMatrix;

          if (tagStart) {

            // remember old namespace
            // unless we're self-closing
            if (!tagEnd) {
              nsMatrixStack.push(_nsMatrix);
            }

            if (cachedAttrs === null) {

              // quick check, whether there may be namespace
              // declarations on the node; if that is the case
              // we need to eagerly parse the node attributes
              if ((maybeNS = x.indexOf('xmlns', q) !== -1)) {
                attrsStart = q;
                attrsString = x;

                getAttrs();

                maybeNS = false;
              }
            }
          }

          _elementName = elementName;

          w = elementName.indexOf(':');
          if (w !== -1) {
            xmlns = nsMatrix[elementName.substring(0, w)];

            // prefix given; namespace must exist
            if (!xmlns) {
              return handleError('missing namespace on <' + _elementName + '>');
            }

            elementName = elementName.substr(w + 1);
          } else {
            xmlns = nsMatrix['xmlns'];

            // if no default namespace is defined,
            // we'll import the element as anonymous.
            //
            // it is up to users to correct that to the document defined
            // targetNamespace, or whatever their undersanding of the
            // XML spec mandates.
          }

          // adjust namespace prefixs as configured
          if (xmlns) {
            elementName = xmlns + ':' + elementName;
          }

        }

        if (tagStart) {
          attrsStart = q;
          attrsString = x;

          if (onOpenTag) {
            if (proxy) {
              onOpenTag(elementProxy, decodeEntities, tagEnd, getContext);
            } else {
              onOpenTag(elementName, getAttrs, decodeEntities, tagEnd, getContext);
            }

            if (parseStop) {
              return;
            }
          }

        }

        if (tagEnd) {

          if (onCloseTag) {
            onCloseTag(proxy ? elementProxy : elementName, decodeEntities, tagStart, getContext);

            if (parseStop) {
              return;
            }
          }

          // restore old namespace
          if (isNamespace) {
            if (!tagStart) {
              nsMatrix = nsMatrixStack.pop();
            } else {
              nsMatrix = _nsMatrix;
            }
          }
        }

        j += 1;
      }
    } /** end parse */

  }

  function hasLowerCaseAlias(pkg) {
    return pkg.xml && pkg.xml.tagAlias === 'lowerCase';
  }

  var DEFAULT_NS_MAP = {
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
    'xml': 'http://www.w3.org/XML/1998/namespace'
  };

  var SERIALIZE_PROPERTY = 'property';

  function getSerialization(element) {
    return element.xml && element.xml.serialize;
  }

  function getSerializationType(element) {
    const type = getSerialization(element);

    return type !== SERIALIZE_PROPERTY && (type || null);
  }

  function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  function aliasToName(aliasNs, pkg) {

    if (!hasLowerCaseAlias(pkg)) {
      return aliasNs.name;
    }

    return aliasNs.prefix + ':' + capitalize(aliasNs.localName);
  }

  /**
   * Un-prefix a potentially prefixed type name.
   *
   * @param {NsName} nameNs
   * @param {Object} [pkg]
   *
   * @return {string}
   */
  function prefixedToName(nameNs, pkg) {

    var name = nameNs.name,
        localName = nameNs.localName;

    var typePrefix = pkg && pkg.xml && pkg.xml.typePrefix;

    if (typePrefix && localName.indexOf(typePrefix) === 0) {
      return nameNs.prefix + ':' + localName.slice(typePrefix.length);
    } else {
      return name;
    }
  }

  function normalizeTypeName(name, nsMap, model) {

    // normalize against actual NS
    const nameNs = parseName(name, nsMap.xmlns);

    const normalizedName = `${ nsMap[nameNs.prefix] || nameNs.prefix }:${ nameNs.localName }`;

    const normalizedNameNs = parseName(normalizedName);

    // determine actual type name, based on package-defined prefix
    var pkg = model.getPackage(normalizedNameNs.prefix);

    return prefixedToName(normalizedNameNs, pkg);
  }

  function error(message) {
    return new Error(message);
  }

  /**
   * Get the moddle descriptor for a given instance or type.
   *
   * @param  {ModdleElement|Function} element
   *
   * @return {Object} the moddle descriptor
   */
  function getModdleDescriptor(element) {
    return element.$descriptor;
  }


  /**
   * A parse context.
   *
   * @class
   *
   * @param {Object} options
   * @param {ElementHandler} options.rootHandler the root handler for parsing a document
   * @param {boolean} [options.lax=false] whether or not to ignore invalid elements
   */
  function Context(options) {

    /**
     * @property {ElementHandler} rootHandler
     */

    /**
     * @property {Boolean} lax
     */

    assign(this, options);

    this.elementsById = {};
    this.references = [];
    this.warnings = [];

    /**
     * Add an unresolved reference.
     *
     * @param {Object} reference
     */
    this.addReference = function(reference) {
      this.references.push(reference);
    };

    /**
     * Add a processed element.
     *
     * @param {ModdleElement} element
     */
    this.addElement = function(element) {

      if (!element) {
        throw error('expected element');
      }

      var elementsById = this.elementsById;

      var descriptor = getModdleDescriptor(element);

      var idProperty = descriptor.idProperty,
          id;

      if (idProperty) {
        id = element.get(idProperty.name);

        if (id) {

          // for QName validation as per http://www.w3.org/TR/REC-xml/#NT-NameChar
          if (!/^([a-z][\w-.]*:)?[a-z_][\w-.]*$/i.test(id)) {
            throw new Error('illegal ID <' + id + '>');
          }

          if (elementsById[id]) {
            throw error('duplicate ID <' + id + '>');
          }

          elementsById[id] = element;
        }
      }
    };

    /**
     * Add an import warning.
     *
     * @param {Object} warning
     * @param {String} warning.message
     * @param {Error} [warning.error]
     */
    this.addWarning = function(warning) {
      this.warnings.push(warning);
    };
  }

  function BaseHandler() {}

  BaseHandler.prototype.handleEnd = function() {};
  BaseHandler.prototype.handleText = function() {};
  BaseHandler.prototype.handleNode = function() {};


  /**
   * A simple pass through handler that does nothing except for
   * ignoring all input it receives.
   *
   * This is used to ignore unknown elements and
   * attributes.
   */
  function NoopHandler() { }

  NoopHandler.prototype = Object.create(BaseHandler.prototype);

  NoopHandler.prototype.handleNode = function() {
    return this;
  };

  function BodyHandler() {}

  BodyHandler.prototype = Object.create(BaseHandler.prototype);

  BodyHandler.prototype.handleText = function(text) {
    this.body = (this.body || '') + text;
  };

  function ReferenceHandler(property, context) {
    this.property = property;
    this.context = context;
  }

  ReferenceHandler.prototype = Object.create(BodyHandler.prototype);

  ReferenceHandler.prototype.handleNode = function(node) {

    if (this.element) {
      throw error('expected no sub nodes');
    } else {
      this.element = this.createReference(node);
    }

    return this;
  };

  ReferenceHandler.prototype.handleEnd = function() {
    this.element.id = this.body;
  };

  ReferenceHandler.prototype.createReference = function(node) {
    return {
      property: this.property.ns.name,
      id: ''
    };
  };

  function ValueHandler(propertyDesc, element) {
    this.element = element;
    this.propertyDesc = propertyDesc;
  }

  ValueHandler.prototype = Object.create(BodyHandler.prototype);

  ValueHandler.prototype.handleEnd = function() {

    var value = this.body || '',
        element = this.element,
        propertyDesc = this.propertyDesc;

    value = coerceType(propertyDesc.type, value);

    if (propertyDesc.isMany) {
      element.get(propertyDesc.name).push(value);
    } else {
      element.set(propertyDesc.name, value);
    }
  };


  function BaseElementHandler() {}

  BaseElementHandler.prototype = Object.create(BodyHandler.prototype);

  BaseElementHandler.prototype.handleNode = function(node) {
    var parser = this,
        element = this.element;

    if (!element) {
      element = this.element = this.createElement(node);

      this.context.addElement(element);
    } else {
      parser = this.handleChild(node);
    }

    return parser;
  };

  /**
   * @class Reader.ElementHandler
   *
   */
  function ElementHandler(model, typeName, context) {
    this.model = model;
    this.type = model.getType(typeName);
    this.context = context;
  }

  ElementHandler.prototype = Object.create(BaseElementHandler.prototype);

  ElementHandler.prototype.addReference = function(reference) {
    this.context.addReference(reference);
  };

  ElementHandler.prototype.handleText = function(text) {

    var element = this.element,
        descriptor = getModdleDescriptor(element),
        bodyProperty = descriptor.bodyProperty;

    if (!bodyProperty) {
      throw error('unexpected body text <' + text + '>');
    }

    BodyHandler.prototype.handleText.call(this, text);
  };

  ElementHandler.prototype.handleEnd = function() {

    var value = this.body,
        element = this.element,
        descriptor = getModdleDescriptor(element),
        bodyProperty = descriptor.bodyProperty;

    if (bodyProperty && value !== undefined) {
      value = coerceType(bodyProperty.type, value);
      element.set(bodyProperty.name, value);
    }
  };

  /**
   * Create an instance of the model from the given node.
   *
   * @param  {Element} node the xml node
   */
  ElementHandler.prototype.createElement = function(node) {
    var attributes = node.attributes,
        Type = this.type,
        descriptor = getModdleDescriptor(Type),
        context = this.context,
        instance = new Type({}),
        model = this.model,
        propNameNs;

    forEach(attributes, function(value, name) {

      var prop = descriptor.propertiesByName[name],
          values;

      if (prop && prop.isReference) {

        if (!prop.isMany) {
          context.addReference({
            element: instance,
            property: prop.ns.name,
            id: value
          });
        } else {

          // IDREFS: parse references as whitespace-separated list
          values = value.split(' ');

          forEach(values, function(v) {
            context.addReference({
              element: instance,
              property: prop.ns.name,
              id: v
            });
          });
        }

      } else {
        if (prop) {
          value = coerceType(prop.type, value);
        } else if (name === 'xmlns') {
          name = ':' + name;
        } else {
          propNameNs = parseName(name, descriptor.ns.prefix);

          // check whether attribute is defined in a well-known namespace
          // if that is the case we emit a warning to indicate potential misuse
          if (model.getPackage(propNameNs.prefix)) {

            context.addWarning({
              message: 'unknown attribute <' + name + '>',
              element: instance,
              property: name,
              value: value
            });
          }
        }

        instance.set(name, value);
      }
    });

    return instance;
  };

  ElementHandler.prototype.getPropertyForNode = function(node) {

    var name = node.name;
    var nameNs = parseName(name);

    var type = this.type,
        model = this.model,
        descriptor = getModdleDescriptor(type);

    var propertyName = nameNs.name,
        property = descriptor.propertiesByName[propertyName];

    // search for properties by name first

    if (property && !property.isAttr) {

      const serializationType = getSerializationType(property);

      if (serializationType) {
        const elementTypeName = node.attributes[serializationType];

        // type is optional, if it does not exists the
        // default type is assumed
        if (elementTypeName) {

          // convert the prefix used to the mapped form, but also
          // take possible type prefixes from XML
          // into account, i.e.: xsi:type="t{ActualType}",
          const normalizedTypeName = normalizeTypeName(elementTypeName, node.ns, model);

          const elementType = model.getType(normalizedTypeName);

          return assign({}, property, {
            effectiveType: getModdleDescriptor(elementType).name
          });
        }
      }

      // search for properties by name first
      return property;
    }

    var pkg = model.getPackage(nameNs.prefix);

    if (pkg) {
      const elementTypeName = aliasToName(nameNs, pkg);
      const elementType = model.getType(elementTypeName);

      // search for collection members later
      property = find(descriptor.properties, function(p) {
        return !p.isVirtual && !p.isReference && !p.isAttribute && elementType.hasType(p.type);
      });

      if (property) {
        return assign({}, property, {
          effectiveType: getModdleDescriptor(elementType).name
        });
      }
    } else {

      // parse unknown element (maybe extension)
      property = find(descriptor.properties, function(p) {
        return !p.isReference && !p.isAttribute && p.type === 'Element';
      });

      if (property) {
        return property;
      }
    }

    throw error('unrecognized element <' + nameNs.name + '>');
  };

  ElementHandler.prototype.toString = function() {
    return 'ElementDescriptor[' + getModdleDescriptor(this.type).name + ']';
  };

  ElementHandler.prototype.valueHandler = function(propertyDesc, element) {
    return new ValueHandler(propertyDesc, element);
  };

  ElementHandler.prototype.referenceHandler = function(propertyDesc) {
    return new ReferenceHandler(propertyDesc, this.context);
  };

  ElementHandler.prototype.handler = function(type) {
    if (type === 'Element') {
      return new GenericElementHandler(this.model, type, this.context);
    } else {
      return new ElementHandler(this.model, type, this.context);
    }
  };

  /**
   * Handle the child element parsing
   *
   * @param  {Element} node the xml node
   */
  ElementHandler.prototype.handleChild = function(node) {
    var propertyDesc, type, element, childHandler;

    propertyDesc = this.getPropertyForNode(node);
    element = this.element;

    type = propertyDesc.effectiveType || propertyDesc.type;

    if (isSimple(type)) {
      return this.valueHandler(propertyDesc, element);
    }

    if (propertyDesc.isReference) {
      childHandler = this.referenceHandler(propertyDesc).handleNode(node);
    } else {
      childHandler = this.handler(type).handleNode(node);
    }

    var newElement = childHandler.element;

    // child handles may decide to skip elements
    // by not returning anything
    if (newElement !== undefined) {

      if (propertyDesc.isMany) {
        element.get(propertyDesc.name).push(newElement);
      } else {
        element.set(propertyDesc.name, newElement);
      }

      if (propertyDesc.isReference) {
        assign(newElement, {
          element: element
        });

        this.context.addReference(newElement);
      } else {

        // establish child -> parent relationship
        newElement.$parent = element;
      }
    }

    return childHandler;
  };

  /**
   * An element handler that performs special validation
   * to ensure the node it gets initialized with matches
   * the handlers type (namespace wise).
   *
   * @param {Moddle} model
   * @param {String} typeName
   * @param {Context} context
   */
  function RootElementHandler(model, typeName, context) {
    ElementHandler.call(this, model, typeName, context);
  }

  RootElementHandler.prototype = Object.create(ElementHandler.prototype);

  RootElementHandler.prototype.createElement = function(node) {

    var name = node.name,
        nameNs = parseName(name),
        model = this.model,
        type = this.type,
        pkg = model.getPackage(nameNs.prefix),
        typeName = pkg && aliasToName(nameNs, pkg) || name;

    // verify the correct namespace if we parse
    // the first element in the handler tree
    //
    // this ensures we don't mistakenly import wrong namespace elements
    if (!type.hasType(typeName)) {
      throw error('unexpected element <' + node.originalName + '>');
    }

    return ElementHandler.prototype.createElement.call(this, node);
  };


  function GenericElementHandler(model, typeName, context) {
    this.model = model;
    this.context = context;
  }

  GenericElementHandler.prototype = Object.create(BaseElementHandler.prototype);

  GenericElementHandler.prototype.createElement = function(node) {

    var name = node.name,
        ns = parseName(name),
        prefix = ns.prefix,
        uri = node.ns[prefix + '$uri'],
        attributes = node.attributes;

    return this.model.createAny(name, uri, attributes);
  };

  GenericElementHandler.prototype.handleChild = function(node) {

    var handler = new GenericElementHandler(this.model, 'Element', this.context).handleNode(node),
        element = this.element;

    var newElement = handler.element,
        children;

    if (newElement !== undefined) {
      children = element.$children = element.$children || [];
      children.push(newElement);

      // establish child -> parent relationship
      newElement.$parent = element;
    }

    return handler;
  };

  GenericElementHandler.prototype.handleEnd = function() {
    if (this.body) {
      this.element.$body = this.body;
    }
  };

  /**
   * A reader for a meta-model
   *
   * @param {Object} options
   * @param {Model} options.model used to read xml files
   * @param {Boolean} options.lax whether to make parse errors warnings
   */
  function Reader(options) {

    if (options instanceof Moddle) {
      options = {
        model: options
      };
    }

    assign(this, { lax: false }, options);
  }

  /**
   * The fromXML result.
   *
   * @typedef {Object} ParseResult
   *
   * @property {ModdleElement} rootElement
   * @property {Array<Object>} references
   * @property {Array<Error>} warnings
   * @property {Object} elementsById - a mapping containing each ID -> ModdleElement
   */

  /**
   * The fromXML result.
   *
   * @typedef {Error} ParseError
   *
   * @property {Array<Error>} warnings
   */

  /**
   * Parse the given XML into a moddle document tree.
   *
   * @param {String} xml
   * @param {ElementHandler|Object} options or rootHandler
   *
   * @returns {Promise<ParseResult, ParseError>}
   */
  Reader.prototype.fromXML = function(xml, options, done) {

    var rootHandler = options.rootHandler;

    if (options instanceof ElementHandler) {

      // root handler passed via (xml, { rootHandler: ElementHandler }, ...)
      rootHandler = options;
      options = {};
    } else {
      if (typeof options === 'string') {

        // rootHandler passed via (xml, 'someString', ...)
        rootHandler = this.handler(options);
        options = {};
      } else if (typeof rootHandler === 'string') {

        // rootHandler passed via (xml, { rootHandler: 'someString' }, ...)
        rootHandler = this.handler(rootHandler);
      }
    }

    var model = this.model,
        lax = this.lax;

    var context = new Context(assign({}, options, { rootHandler: rootHandler })),
        parser = new Parser({ proxy: true }),
        stack = createStack();

    rootHandler.context = context;

    // push root handler
    stack.push(rootHandler);


    /**
     * Handle error.
     *
     * @param  {Error} err
     * @param  {Function} getContext
     * @param  {boolean} lax
     *
     * @return {boolean} true if handled
     */
    function handleError(err, getContext, lax) {

      var ctx = getContext();

      var line = ctx.line,
          column = ctx.column,
          data = ctx.data;

      // we receive the full context data here,
      // for elements trim down the information
      // to the tag name, only
      if (data.charAt(0) === '<' && data.indexOf(' ') !== -1) {
        data = data.slice(0, data.indexOf(' ')) + '>';
      }

      var message =
        'unparsable content ' + (data ? data + ' ' : '') + 'detected\n\t' +
          'line: ' + line + '\n\t' +
          'column: ' + column + '\n\t' +
          'nested error: ' + err.message;

      if (lax) {
        context.addWarning({
          message: message,
          error: err
        });

        return true;
      } else {
        throw error(message);
      }
    }

    function handleWarning(err, getContext) {

      // just like handling errors in <lax=true> mode
      return handleError(err, getContext, true);
    }

    /**
     * Resolve collected references on parse end.
     */
    function resolveReferences() {

      var elementsById = context.elementsById;
      var references = context.references;

      var i, r;

      for (i = 0; (r = references[i]); i++) {
        var element = r.element;
        var reference = elementsById[r.id];
        var property = getModdleDescriptor(element).propertiesByName[r.property];

        if (!reference) {
          context.addWarning({
            message: 'unresolved reference <' + r.id + '>',
            element: r.element,
            property: r.property,
            value: r.id
          });
        }

        if (property.isMany) {
          var collection = element.get(property.name),
              idx = collection.indexOf(r);

          // we replace an existing place holder (idx != -1) or
          // append to the collection instead
          if (idx === -1) {
            idx = collection.length;
          }

          if (!reference) {

            // remove unresolvable reference
            collection.splice(idx, 1);
          } else {

            // add or update reference in collection
            collection[idx] = reference;
          }
        } else {
          element.set(property.name, reference);
        }
      }
    }

    function handleClose() {
      stack.pop().handleEnd();
    }

    var PREAMBLE_START_PATTERN = /^<\?xml /i;

    var ENCODING_PATTERN = / encoding="([^"]+)"/i;

    var UTF_8_PATTERN = /^utf-8$/i;

    function handleQuestion(question) {

      if (!PREAMBLE_START_PATTERN.test(question)) {
        return;
      }

      var match = ENCODING_PATTERN.exec(question);
      var encoding = match && match[1];

      if (!encoding || UTF_8_PATTERN.test(encoding)) {
        return;
      }

      context.addWarning({
        message:
          'unsupported document encoding <' + encoding + '>, ' +
          'falling back to UTF-8'
      });
    }

    function handleOpen(node, getContext) {
      var handler = stack.peek();

      try {
        stack.push(handler.handleNode(node));
      } catch (err) {

        if (handleError(err, getContext, lax)) {
          stack.push(new NoopHandler());
        }
      }
    }

    function handleCData(text, getContext) {

      try {
        stack.peek().handleText(text);
      } catch (err) {
        handleWarning(err, getContext);
      }
    }

    function handleText(text, getContext) {

      // strip whitespace only nodes, i.e. before
      // <!CDATA[ ... ]> sections and in between tags

      if (!text.trim()) {
        return;
      }

      handleCData(text, getContext);
    }

    var uriMap = model.getPackages().reduce(function(uriMap, p) {
      uriMap[p.uri] = p.prefix;

      return uriMap;
    }, Object.entries(DEFAULT_NS_MAP).reduce(function(map, [ prefix, url ]) {
      map[url] = prefix;

      return map;
    }, model.config && model.config.nsMap || {}));

    parser
      .ns(uriMap)
      .on('openTag', function(obj, decodeStr, selfClosing, getContext) {

        // gracefully handle unparsable attributes (attrs=false)
        var attrs = obj.attrs || {};

        var decodedAttrs = Object.keys(attrs).reduce(function(d, key) {
          var value = decodeStr(attrs[key]);

          d[key] = value;

          return d;
        }, {});

        var node = {
          name: obj.name,
          originalName: obj.originalName,
          attributes: decodedAttrs,
          ns: obj.ns
        };

        handleOpen(node, getContext);
      })
      .on('question', handleQuestion)
      .on('closeTag', handleClose)
      .on('cdata', handleCData)
      .on('text', function(text, decodeEntities, getContext) {
        handleText(decodeEntities(text), getContext);
      })
      .on('error', handleError)
      .on('warn', handleWarning);

    // async XML parsing to make sure the execution environment
    // (node or brower) is kept responsive and that certain optimization
    // strategies can kick in.
    return new Promise(function(resolve, reject) {

      var err;

      try {
        parser.parse(xml);

        resolveReferences();
      } catch (e) {
        err = e;
      }

      var rootElement = rootHandler.element;

      if (!err && !rootElement) {
        err = error('failed to parse document as <' + rootHandler.type.$descriptor.name + '>');
      }

      var warnings = context.warnings;
      var references = context.references;
      var elementsById = context.elementsById;

      if (err) {
        err.warnings = warnings;

        return reject(err);
      } else {
        return resolve({
          rootElement: rootElement,
          elementsById: elementsById,
          references: references,
          warnings: warnings
        });
      }
    });
  };

  Reader.prototype.handler = function(name) {
    return new RootElementHandler(this.model, name);
  };


  // helpers //////////////////////////

  function createStack() {
    var stack = [];

    Object.defineProperty(stack, 'peek', {
      value: function() {
        return this[this.length - 1];
      }
    });

    return stack;
  }

  var XML_PREAMBLE = '<?xml version="1.0" encoding="UTF-8"?>\n';

  var ESCAPE_ATTR_CHARS = /<|>|'|"|&|\n\r|\n/g;
  var ESCAPE_CHARS = /<|>|&/g;


  function Namespaces(parent) {

    this.prefixMap = {};
    this.uriMap = {};
    this.used = {};

    this.wellknown = [];
    this.custom = [];
    this.parent = parent;

    this.defaultPrefixMap = parent && parent.defaultPrefixMap || {};
  }

  Namespaces.prototype.mapDefaultPrefixes = function(defaultPrefixMap) {
    this.defaultPrefixMap = defaultPrefixMap;
  };

  Namespaces.prototype.defaultUriByPrefix = function(prefix) {
    return this.defaultPrefixMap[prefix];
  };

  Namespaces.prototype.byUri = function(uri) {
    return this.uriMap[uri] || (
      this.parent && this.parent.byUri(uri)
    );
  };

  Namespaces.prototype.add = function(ns, isWellknown) {

    this.uriMap[ns.uri] = ns;

    if (isWellknown) {
      this.wellknown.push(ns);
    } else {
      this.custom.push(ns);
    }

    this.mapPrefix(ns.prefix, ns.uri);
  };

  Namespaces.prototype.uriByPrefix = function(prefix) {
    return this.prefixMap[prefix || 'xmlns'] || (
      this.parent && this.parent.uriByPrefix(prefix)
    );
  };

  Namespaces.prototype.mapPrefix = function(prefix, uri) {
    this.prefixMap[prefix || 'xmlns'] = uri;
  };

  Namespaces.prototype.getNSKey = function(ns) {
    return (ns.prefix !== undefined) ? (ns.uri + '|' + ns.prefix) : ns.uri;
  };

  Namespaces.prototype.logUsed = function(ns) {

    var uri = ns.uri;
    var nsKey = this.getNSKey(ns);

    this.used[nsKey] = this.byUri(uri);

    // Inform parent recursively about the usage of this NS
    if (this.parent) {
      this.parent.logUsed(ns);
    }
  };

  Namespaces.prototype.getUsed = function(ns) {

    var allNs = [].concat(this.wellknown, this.custom);

    return allNs.filter(ns => {
      var nsKey = this.getNSKey(ns);

      return this.used[nsKey];
    });
  };


  function lower(string) {
    return string.charAt(0).toLowerCase() + string.slice(1);
  }

  function nameToAlias(name, pkg) {
    if (hasLowerCaseAlias(pkg)) {
      return lower(name);
    } else {
      return name;
    }
  }

  function inherits(ctor, superCtor) {
    ctor.super_ = superCtor;
    ctor.prototype = Object.create(superCtor.prototype, {
      constructor: {
        value: ctor,
        enumerable: false,
        writable: true,
        configurable: true
      }
    });
  }

  function nsName(ns) {
    if (isString(ns)) {
      return ns;
    } else {
      return (ns.prefix ? ns.prefix + ':' : '') + ns.localName;
    }
  }

  function getNsAttrs(namespaces) {

    return namespaces.getUsed().filter(function(ns) {

      // do not serialize built in <xml> namespace
      return ns.prefix !== 'xml';
    }).map(function(ns) {
      var name = 'xmlns' + (ns.prefix ? ':' + ns.prefix : '');
      return { name: name, value: ns.uri };
    });

  }

  function getElementNs(ns, descriptor) {
    if (descriptor.isGeneric) {
      return assign({ localName: descriptor.ns.localName }, ns);
    } else {
      return assign({ localName: nameToAlias(descriptor.ns.localName, descriptor.$pkg) }, ns);
    }
  }

  function getPropertyNs(ns, descriptor) {
    return assign({ localName: descriptor.ns.localName }, ns);
  }

  function getSerializableProperties(element) {
    var descriptor = element.$descriptor;

    return filter(descriptor.properties, function(p) {
      var name = p.name;

      if (p.isVirtual) {
        return false;
      }

      // do not serialize defaults
      if (!has(element, name)) {
        return false;
      }

      var value = element[name];

      // do not serialize default equals
      if (value === p.default) {
        return false;
      }

      // do not serialize null properties
      if (value === null) {
        return false;
      }

      return p.isMany ? value.length : true;
    });
  }

  var ESCAPE_ATTR_MAP = {
    '\n': '#10',
    '\n\r': '#10',
    '"': '#34',
    '\'': '#39',
    '<': '#60',
    '>': '#62',
    '&': '#38'
  };

  var ESCAPE_MAP = {
    '<': 'lt',
    '>': 'gt',
    '&': 'amp'
  };

  function escape(str, charPattern, replaceMap) {

    // ensure we are handling strings here
    str = isString(str) ? str : '' + str;

    return str.replace(charPattern, function(s) {
      return '&' + replaceMap[s] + ';';
    });
  }

  /**
   * Escape a string attribute to not contain any bad values (line breaks, '"', ...)
   *
   * @param {String} str the string to escape
   * @return {String} the escaped string
   */
  function escapeAttr(str) {
    return escape(str, ESCAPE_ATTR_CHARS, ESCAPE_ATTR_MAP);
  }

  function escapeBody(str) {
    return escape(str, ESCAPE_CHARS, ESCAPE_MAP);
  }

  function filterAttributes(props) {
    return filter(props, function(p) { return p.isAttr; });
  }

  function filterContained(props) {
    return filter(props, function(p) { return !p.isAttr; });
  }


  function ReferenceSerializer(tagName) {
    this.tagName = tagName;
  }

  ReferenceSerializer.prototype.build = function(element) {
    this.element = element;
    return this;
  };

  ReferenceSerializer.prototype.serializeTo = function(writer) {
    writer
      .appendIndent()
      .append('<' + this.tagName + '>' + this.element.id + '</' + this.tagName + '>')
      .appendNewLine();
  };

  function BodySerializer() {}

  BodySerializer.prototype.serializeValue =
  BodySerializer.prototype.serializeTo = function(writer) {
    writer.append(
      this.escape
        ? escapeBody(this.value)
        : this.value
    );
  };

  BodySerializer.prototype.build = function(prop, value) {
    this.value = value;

    if (prop.type === 'String' && value.search(ESCAPE_CHARS) !== -1) {
      this.escape = true;
    }

    return this;
  };

  function ValueSerializer(tagName) {
    this.tagName = tagName;
  }

  inherits(ValueSerializer, BodySerializer);

  ValueSerializer.prototype.serializeTo = function(writer) {

    writer
      .appendIndent()
      .append('<' + this.tagName + '>');

    this.serializeValue(writer);

    writer
      .append('</' + this.tagName + '>')
      .appendNewLine();
  };

  function ElementSerializer(parent, propertyDescriptor) {
    this.body = [];
    this.attrs = [];

    this.parent = parent;
    this.propertyDescriptor = propertyDescriptor;
  }

  ElementSerializer.prototype.build = function(element) {
    this.element = element;

    var elementDescriptor = element.$descriptor,
        propertyDescriptor = this.propertyDescriptor;

    var otherAttrs,
        properties;

    var isGeneric = elementDescriptor.isGeneric;

    if (isGeneric) {
      otherAttrs = this.parseGenericNsAttributes(element);
    } else {
      otherAttrs = this.parseNsAttributes(element);
    }

    if (propertyDescriptor) {
      this.ns = this.nsPropertyTagName(propertyDescriptor);
    } else {
      this.ns = this.nsTagName(elementDescriptor);
    }

    // compute tag name
    this.tagName = this.addTagName(this.ns);

    if (isGeneric) {
      this.parseGenericContainments(element);
    } else {
      properties = getSerializableProperties(element);

      this.parseAttributes(filterAttributes(properties));
      this.parseContainments(filterContained(properties));
    }

    this.parseGenericAttributes(element, otherAttrs);

    return this;
  };

  ElementSerializer.prototype.nsTagName = function(descriptor) {
    var effectiveNs = this.logNamespaceUsed(descriptor.ns);
    return getElementNs(effectiveNs, descriptor);
  };

  ElementSerializer.prototype.nsPropertyTagName = function(descriptor) {
    var effectiveNs = this.logNamespaceUsed(descriptor.ns);
    return getPropertyNs(effectiveNs, descriptor);
  };

  ElementSerializer.prototype.isLocalNs = function(ns) {
    return ns.uri === this.ns.uri;
  };

  /**
   * Get the actual ns attribute name for the given element.
   *
   * @param {Object} element
   * @param {Boolean} [element.inherited=false]
   *
   * @return {Object} nsName
   */
  ElementSerializer.prototype.nsAttributeName = function(element) {

    var ns;

    if (isString(element)) {
      ns = parseName(element);
    } else {
      ns = element.ns;
    }

    // return just local name for inherited attributes
    if (element.inherited) {
      return { localName: ns.localName };
    }

    // parse + log effective ns
    var effectiveNs = this.logNamespaceUsed(ns);

    // LOG ACTUAL namespace use
    this.getNamespaces().logUsed(effectiveNs);

    // strip prefix if same namespace like parent
    if (this.isLocalNs(effectiveNs)) {
      return { localName: ns.localName };
    } else {
      return assign({ localName: ns.localName }, effectiveNs);
    }
  };

  ElementSerializer.prototype.parseGenericNsAttributes = function(element) {

    return Object.entries(element).filter(
      ([ key, value ]) => !key.startsWith('$') && this.parseNsAttribute(element, key, value)
    ).map(
      ([ key, value ]) => ({ name: key, value: value })
    );
  };

  ElementSerializer.prototype.parseGenericContainments = function(element) {
    var body = element.$body;

    if (body) {
      this.body.push(new BodySerializer().build({ type: 'String' }, body));
    }

    var children = element.$children;

    if (children) {
      forEach(children, child => {
        this.body.push(new ElementSerializer(this).build(child));
      });
    }
  };

  ElementSerializer.prototype.parseNsAttribute = function(element, name, value) {
    var model = element.$model;

    var nameNs = parseName(name);

    var ns;

    // parse xmlns:foo="http://foo.bar"
    if (nameNs.prefix === 'xmlns') {
      ns = { prefix: nameNs.localName, uri: value };
    }

    // parse xmlns="http://foo.bar"
    if (!nameNs.prefix && nameNs.localName === 'xmlns') {
      ns = { uri: value };
    }

    if (!ns) {
      return {
        name: name,
        value: value
      };
    }

    if (model && model.getPackage(value)) {

      // register well known namespace
      this.logNamespace(ns, true, true);
    } else {

      // log custom namespace directly as used
      var actualNs = this.logNamespaceUsed(ns, true);

      this.getNamespaces().logUsed(actualNs);
    }
  };


  /**
   * Parse namespaces and return a list of left over generic attributes
   *
   * @param  {Object} element
   * @return {Array<Object>}
   */
  ElementSerializer.prototype.parseNsAttributes = function(element) {
    var self = this;

    var genericAttrs = element.$attrs;

    var attributes = [];

    // parse namespace attributes first
    // and log them. push non namespace attributes to a list
    // and process them later
    forEach(genericAttrs, function(value, name) {

      var nonNsAttr = self.parseNsAttribute(element, name, value);

      if (nonNsAttr) {
        attributes.push(nonNsAttr);
      }
    });

    return attributes;
  };

  ElementSerializer.prototype.parseGenericAttributes = function(element, attributes) {

    var self = this;

    forEach(attributes, function(attr) {

      try {
        self.addAttribute(self.nsAttributeName(attr.name), attr.value);
      } catch (e) {

        // eslint-disable-next-line no-undef
        typeof console !== 'undefined' && console.warn(
          `missing namespace information for <${
          attr.name
        }=${ attr.value }> on`, element, e
        );
      }
    });
  };

  ElementSerializer.prototype.parseContainments = function(properties) {

    var self = this,
        body = this.body,
        element = this.element;

    forEach(properties, function(p) {
      var value = element.get(p.name),
          isReference = p.isReference,
          isMany = p.isMany;

      if (!isMany) {
        value = [ value ];
      }

      if (p.isBody) {
        body.push(new BodySerializer().build(p, value[0]));
      } else if (isSimple(p.type)) {
        forEach(value, function(v) {
          body.push(new ValueSerializer(self.addTagName(self.nsPropertyTagName(p))).build(p, v));
        });
      } else if (isReference) {
        forEach(value, function(v) {
          body.push(new ReferenceSerializer(self.addTagName(self.nsPropertyTagName(p))).build(v));
        });
      } else {

        // allow serialization via type
        // rather than element name
        var serialization = getSerialization(p);

        forEach(value, function(v) {
          var serializer;

          if (serialization) {
            if (serialization === SERIALIZE_PROPERTY) {
              serializer = new ElementSerializer(self, p);
            } else {
              serializer = new TypeSerializer(self, p, serialization);
            }
          } else {
            serializer = new ElementSerializer(self);
          }

          body.push(serializer.build(v));
        });
      }
    });
  };

  ElementSerializer.prototype.getNamespaces = function(local) {

    var namespaces = this.namespaces,
        parent = this.parent,
        parentNamespaces;

    if (!namespaces) {
      parentNamespaces = parent && parent.getNamespaces();

      if (local || !parentNamespaces) {
        this.namespaces = namespaces = new Namespaces(parentNamespaces);
      } else {
        namespaces = parentNamespaces;
      }
    }

    return namespaces;
  };

  ElementSerializer.prototype.logNamespace = function(ns, wellknown, local) {
    var namespaces = this.getNamespaces(local);

    var nsUri = ns.uri,
        nsPrefix = ns.prefix;

    var existing = namespaces.byUri(nsUri);

    if (!existing || local) {
      namespaces.add(ns, wellknown);
    }

    namespaces.mapPrefix(nsPrefix, nsUri);

    return ns;
  };

  ElementSerializer.prototype.logNamespaceUsed = function(ns, local) {
    var namespaces = this.getNamespaces(local);

    // ns may be
    //
    //   * prefix only
    //   * prefix:uri
    //   * localName only

    var prefix = ns.prefix,
        uri = ns.uri,
        newPrefix, idx,
        wellknownUri;

    // handle anonymous namespaces (elementForm=unqualified), cf. #23
    if (!prefix && !uri) {
      return { localName: ns.localName };
    }

    wellknownUri = namespaces.defaultUriByPrefix(prefix);

    uri = uri || wellknownUri || namespaces.uriByPrefix(prefix);

    if (!uri) {
      throw new Error('no namespace uri given for prefix <' + prefix + '>');
    }

    ns = namespaces.byUri(uri);

    // register new default prefix <xmlns> in local scope
    if (!ns && !prefix) {
      ns = this.logNamespace({ uri }, wellknownUri === uri, true);
    }

    if (!ns) {
      newPrefix = prefix;
      idx = 1;

      // find a prefix that is not mapped yet
      while (namespaces.uriByPrefix(newPrefix)) {
        newPrefix = prefix + '_' + idx++;
      }

      ns = this.logNamespace({ prefix: newPrefix, uri: uri }, wellknownUri === uri);
    }

    if (prefix) {
      namespaces.mapPrefix(prefix, uri);
    }

    return ns;
  };

  ElementSerializer.prototype.parseAttributes = function(properties) {
    var self = this,
        element = this.element;

    forEach(properties, function(p) {

      var value = element.get(p.name);

      if (p.isReference) {

        if (!p.isMany) {
          value = value.id;
        } else {
          var values = [];
          forEach(value, function(v) {
            values.push(v.id);
          });

          // IDREFS is a whitespace-separated list of references.
          value = values.join(' ');
        }

      }

      self.addAttribute(self.nsAttributeName(p), value);
    });
  };

  ElementSerializer.prototype.addTagName = function(nsTagName) {
    var actualNs = this.logNamespaceUsed(nsTagName);

    this.getNamespaces().logUsed(actualNs);

    return nsName(nsTagName);
  };

  ElementSerializer.prototype.addAttribute = function(name, value) {
    var attrs = this.attrs;

    if (isString(value)) {
      value = escapeAttr(value);
    }

    // de-duplicate attributes
    // https://github.com/bpmn-io/moddle-xml/issues/66
    var idx = findIndex(attrs, function(element) {
      return (
        element.name.localName === name.localName &&
        element.name.uri === name.uri &&
        element.name.prefix === name.prefix
      );
    });

    var attr = { name: name, value: value };

    if (idx !== -1) {
      attrs.splice(idx, 1, attr);
    } else {
      attrs.push(attr);
    }
  };

  ElementSerializer.prototype.serializeAttributes = function(writer) {
    var attrs = this.attrs,
        namespaces = this.namespaces;

    if (namespaces) {
      attrs = getNsAttrs(namespaces).concat(attrs);
    }

    forEach(attrs, function(a) {
      writer
        .append(' ')
        .append(nsName(a.name)).append('="').append(a.value).append('"');
    });
  };

  ElementSerializer.prototype.serializeTo = function(writer) {
    var firstBody = this.body[0],
        indent = firstBody && firstBody.constructor !== BodySerializer;

    writer
      .appendIndent()
      .append('<' + this.tagName);

    this.serializeAttributes(writer);

    writer.append(firstBody ? '>' : ' />');

    if (firstBody) {

      if (indent) {
        writer
          .appendNewLine()
          .indent();
      }

      forEach(this.body, function(b) {
        b.serializeTo(writer);
      });

      if (indent) {
        writer
          .unindent()
          .appendIndent();
      }

      writer.append('</' + this.tagName + '>');
    }

    writer.appendNewLine();
  };

  /**
   * A serializer for types that handles serialization of data types
   */
  function TypeSerializer(parent, propertyDescriptor, serialization) {
    ElementSerializer.call(this, parent, propertyDescriptor);

    this.serialization = serialization;
  }

  inherits(TypeSerializer, ElementSerializer);

  TypeSerializer.prototype.parseNsAttributes = function(element) {

    // extracted attributes with serialization attribute
    // <type=typeName> stripped; it may be later
    var attributes = ElementSerializer.prototype.parseNsAttributes.call(this, element).filter(
      attr => attr.name !== this.serialization
    );

    var descriptor = element.$descriptor;

    // only serialize <type=typeName> if necessary
    if (descriptor.name === this.propertyDescriptor.type) {
      return attributes;
    }

    var typeNs = this.typeNs = this.nsTagName(descriptor);
    this.getNamespaces().logUsed(this.typeNs);

    // add xsi:type attribute to represent the elements
    // actual type

    var pkg = element.$model.getPackage(typeNs.uri),
        typePrefix = (pkg.xml && pkg.xml.typePrefix) || '';

    this.addAttribute(
      this.nsAttributeName(this.serialization),
      (typeNs.prefix ? typeNs.prefix + ':' : '') + typePrefix + descriptor.ns.localName
    );

    return attributes;
  };

  TypeSerializer.prototype.isLocalNs = function(ns) {
    return ns.uri === (this.typeNs || this.ns).uri;
  };

  function SavingWriter() {
    this.value = '';

    this.write = function(str) {
      this.value += str;
    };
  }

  function FormatingWriter(out, format) {

    var indent = [ '' ];

    this.append = function(str) {
      out.write(str);

      return this;
    };

    this.appendNewLine = function() {
      if (format) {
        out.write('\n');
      }

      return this;
    };

    this.appendIndent = function() {
      if (format) {
        out.write(indent.join('  '));
      }

      return this;
    };

    this.indent = function() {
      indent.push('');
      return this;
    };

    this.unindent = function() {
      indent.pop();
      return this;
    };
  }

  /**
   * A writer for meta-model backed document trees
   *
   * @param {Object} options output options to pass into the writer
   */
  function Writer(options) {

    options = assign({ format: false, preamble: true }, options || {});

    function toXML(tree, writer) {
      var internalWriter = writer || new SavingWriter();
      var formatingWriter = new FormatingWriter(internalWriter, options.format);

      if (options.preamble) {
        formatingWriter.append(XML_PREAMBLE);
      }

      var serializer = new ElementSerializer();

      var model = tree.$model;

      serializer.getNamespaces().mapDefaultPrefixes(getDefaultPrefixMappings(model));

      serializer.build(tree).serializeTo(formatingWriter);

      if (!writer) {
        return internalWriter.value;
      }
    }

    return {
      toXML: toXML
    };
  }


  // helpers ///////////

  /**
   * @param {Moddle} model
   *
   * @return { Record<string, string> } map from prefix to URI
   */
  function getDefaultPrefixMappings(model) {

    const nsMap = model.config && model.config.nsMap || {};

    const prefixMap = {};

    // { prefix -> uri }
    for (const prefix in DEFAULT_NS_MAP) {
      prefixMap[prefix] = DEFAULT_NS_MAP[prefix];
    }

    // { uri -> prefix }
    for (const uri in nsMap) {
      const prefix = nsMap[uri];

      prefixMap[prefix] = uri;
    }

    for (const pkg of model.getPackages()) {
      prefixMap[pkg.prefix] = pkg.uri;
    }

    return prefixMap;
  }

  /**
   * A sub class of {@link Moddle} with support for import and export of BPMN 2.0 xml files.
   *
   * @class BpmnModdle
   * @extends Moddle
   *
   * @param {Object|Array} packages to use for instantiating the model
   * @param {Object} [options] additional options to pass over
   */
  function BpmnModdle(packages, options) {
    Moddle.call(this, packages, options);
  }

  BpmnModdle.prototype = Object.create(Moddle.prototype);

  /**
   * The fromXML result.
   *
   * @typedef {Object} ParseResult
   *
   * @property {ModdleElement} rootElement
   * @property {Array<Object>} references
   * @property {Array<Error>} warnings
   * @property {Object} elementsById - a mapping containing each ID -> ModdleElement
   */

  /**
   * The fromXML error.
   *
   * @typedef {Error} ParseError
   *
   * @property {Array<Error>} warnings
   */

  /**
   * Instantiates a BPMN model tree from a given xml string.
   *
   * @param {String}   xmlStr
   * @param {String}   [typeName='bpmn:Definitions'] name of the root element
   * @param {Object}   [options]  options to pass to the underlying reader
   *
   * @returns {Promise<ParseResult, ParseError>}
   */
  BpmnModdle.prototype.fromXML = function(xmlStr, typeName, options) {

    if (!isString(typeName)) {
      options = typeName;
      typeName = 'bpmn:Definitions';
    }

    var reader = new Reader(assign({ model: this, lax: true }, options));
    var rootHandler = reader.handler(typeName);

    return reader.fromXML(xmlStr, rootHandler);
  };


  /**
   * The toXML result.
   *
   * @typedef {Object} SerializationResult
   *
   * @property {String} xml
   */

  /**
   * Serializes a BPMN 2.0 object tree to XML.
   *
   * @param {String}   element    the root element, typically an instance of `bpmn:Definitions`
   * @param {Object}   [options]  to pass to the underlying writer
   *
   * @returns {Promise<SerializationResult, Error>}
   */
  BpmnModdle.prototype.toXML = function(element, options) {

    var writer = new Writer(options);

    return new Promise(function(resolve, reject) {
      try {
        var result = writer.toXML(element);

        return resolve({
          xml: result
        });
      } catch (err) {
        return reject(err);
      }
    });
  };

  var name$5 = "BPMN20";
  var uri$5 = "http://www.omg.org/spec/BPMN/20100524/MODEL";
  var prefix$5 = "bpmn";
  var associations$5 = [
  ];
  var types$5 = [
  	{
  		name: "Interface",
  		superClass: [
  			"RootElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "operations",
  				type: "Operation",
  				isMany: true
  			},
  			{
  				name: "implementationRef",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "Operation",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "inMessageRef",
  				type: "Message",
  				isReference: true
  			},
  			{
  				name: "outMessageRef",
  				type: "Message",
  				isReference: true
  			},
  			{
  				name: "errorRef",
  				type: "Error",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "implementationRef",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "EndPoint",
  		superClass: [
  			"RootElement"
  		]
  	},
  	{
  		name: "Auditing",
  		superClass: [
  			"BaseElement"
  		]
  	},
  	{
  		name: "GlobalTask",
  		superClass: [
  			"CallableElement"
  		],
  		properties: [
  			{
  				name: "resources",
  				type: "ResourceRole",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "Monitoring",
  		superClass: [
  			"BaseElement"
  		]
  	},
  	{
  		name: "Performer",
  		superClass: [
  			"ResourceRole"
  		]
  	},
  	{
  		name: "Process",
  		superClass: [
  			"FlowElementsContainer",
  			"CallableElement"
  		],
  		properties: [
  			{
  				name: "processType",
  				type: "ProcessType",
  				isAttr: true
  			},
  			{
  				name: "isClosed",
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "auditing",
  				type: "Auditing"
  			},
  			{
  				name: "monitoring",
  				type: "Monitoring"
  			},
  			{
  				name: "properties",
  				type: "Property",
  				isMany: true
  			},
  			{
  				name: "laneSets",
  				isMany: true,
  				replaces: "FlowElementsContainer#laneSets",
  				type: "LaneSet"
  			},
  			{
  				name: "flowElements",
  				isMany: true,
  				replaces: "FlowElementsContainer#flowElements",
  				type: "FlowElement"
  			},
  			{
  				name: "artifacts",
  				type: "Artifact",
  				isMany: true
  			},
  			{
  				name: "resources",
  				type: "ResourceRole",
  				isMany: true
  			},
  			{
  				name: "correlationSubscriptions",
  				type: "CorrelationSubscription",
  				isMany: true
  			},
  			{
  				name: "supports",
  				type: "Process",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "definitionalCollaborationRef",
  				type: "Collaboration",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "isExecutable",
  				isAttr: true,
  				type: "Boolean"
  			}
  		]
  	},
  	{
  		name: "LaneSet",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "lanes",
  				type: "Lane",
  				isMany: true
  			},
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "Lane",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "partitionElementRef",
  				type: "BaseElement",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "partitionElement",
  				type: "BaseElement"
  			},
  			{
  				name: "flowNodeRef",
  				type: "FlowNode",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "childLaneSet",
  				type: "LaneSet",
  				xml: {
  					serialize: "xsi:type"
  				}
  			}
  		]
  	},
  	{
  		name: "GlobalManualTask",
  		superClass: [
  			"GlobalTask"
  		]
  	},
  	{
  		name: "ManualTask",
  		superClass: [
  			"Task"
  		]
  	},
  	{
  		name: "UserTask",
  		superClass: [
  			"Task"
  		],
  		properties: [
  			{
  				name: "renderings",
  				type: "Rendering",
  				isMany: true
  			},
  			{
  				name: "implementation",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "Rendering",
  		superClass: [
  			"BaseElement"
  		]
  	},
  	{
  		name: "HumanPerformer",
  		superClass: [
  			"Performer"
  		]
  	},
  	{
  		name: "PotentialOwner",
  		superClass: [
  			"HumanPerformer"
  		]
  	},
  	{
  		name: "GlobalUserTask",
  		superClass: [
  			"GlobalTask"
  		],
  		properties: [
  			{
  				name: "implementation",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "renderings",
  				type: "Rendering",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "Gateway",
  		isAbstract: true,
  		superClass: [
  			"FlowNode"
  		],
  		properties: [
  			{
  				name: "gatewayDirection",
  				type: "GatewayDirection",
  				"default": "Unspecified",
  				isAttr: true
  			}
  		]
  	},
  	{
  		name: "EventBasedGateway",
  		superClass: [
  			"Gateway"
  		],
  		properties: [
  			{
  				name: "instantiate",
  				"default": false,
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "eventGatewayType",
  				type: "EventBasedGatewayType",
  				isAttr: true,
  				"default": "Exclusive"
  			}
  		]
  	},
  	{
  		name: "ComplexGateway",
  		superClass: [
  			"Gateway"
  		],
  		properties: [
  			{
  				name: "activationCondition",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			},
  			{
  				name: "default",
  				type: "SequenceFlow",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "ExclusiveGateway",
  		superClass: [
  			"Gateway"
  		],
  		properties: [
  			{
  				name: "default",
  				type: "SequenceFlow",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "InclusiveGateway",
  		superClass: [
  			"Gateway"
  		],
  		properties: [
  			{
  				name: "default",
  				type: "SequenceFlow",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "ParallelGateway",
  		superClass: [
  			"Gateway"
  		]
  	},
  	{
  		name: "RootElement",
  		isAbstract: true,
  		superClass: [
  			"BaseElement"
  		]
  	},
  	{
  		name: "Relationship",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "type",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "direction",
  				type: "RelationshipDirection",
  				isAttr: true
  			},
  			{
  				name: "source",
  				isMany: true,
  				isReference: true,
  				type: "Element"
  			},
  			{
  				name: "target",
  				isMany: true,
  				isReference: true,
  				type: "Element"
  			}
  		]
  	},
  	{
  		name: "BaseElement",
  		isAbstract: true,
  		properties: [
  			{
  				name: "id",
  				isAttr: true,
  				type: "String",
  				isId: true
  			},
  			{
  				name: "documentation",
  				type: "Documentation",
  				isMany: true
  			},
  			{
  				name: "extensionDefinitions",
  				type: "ExtensionDefinition",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "extensionElements",
  				type: "ExtensionElements"
  			}
  		]
  	},
  	{
  		name: "Extension",
  		properties: [
  			{
  				name: "mustUnderstand",
  				"default": false,
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "definition",
  				type: "ExtensionDefinition",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "ExtensionDefinition",
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "extensionAttributeDefinitions",
  				type: "ExtensionAttributeDefinition",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "ExtensionAttributeDefinition",
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "type",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "isReference",
  				"default": false,
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "extensionDefinition",
  				type: "ExtensionDefinition",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "ExtensionElements",
  		properties: [
  			{
  				name: "valueRef",
  				isAttr: true,
  				isReference: true,
  				type: "Element"
  			},
  			{
  				name: "values",
  				type: "Element",
  				isMany: true
  			},
  			{
  				name: "extensionAttributeDefinition",
  				type: "ExtensionAttributeDefinition",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "Documentation",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "text",
  				type: "String",
  				isBody: true
  			},
  			{
  				name: "textFormat",
  				"default": "text/plain",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "Event",
  		isAbstract: true,
  		superClass: [
  			"FlowNode",
  			"InteractionNode"
  		],
  		properties: [
  			{
  				name: "properties",
  				type: "Property",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "IntermediateCatchEvent",
  		superClass: [
  			"CatchEvent"
  		]
  	},
  	{
  		name: "IntermediateThrowEvent",
  		superClass: [
  			"ThrowEvent"
  		]
  	},
  	{
  		name: "EndEvent",
  		superClass: [
  			"ThrowEvent"
  		]
  	},
  	{
  		name: "StartEvent",
  		superClass: [
  			"CatchEvent"
  		],
  		properties: [
  			{
  				name: "isInterrupting",
  				"default": true,
  				isAttr: true,
  				type: "Boolean"
  			}
  		]
  	},
  	{
  		name: "ThrowEvent",
  		isAbstract: true,
  		superClass: [
  			"Event"
  		],
  		properties: [
  			{
  				name: "dataInputs",
  				type: "DataInput",
  				isMany: true
  			},
  			{
  				name: "dataInputAssociations",
  				type: "DataInputAssociation",
  				isMany: true
  			},
  			{
  				name: "inputSet",
  				type: "InputSet"
  			},
  			{
  				name: "eventDefinitions",
  				type: "EventDefinition",
  				isMany: true
  			},
  			{
  				name: "eventDefinitionRef",
  				type: "EventDefinition",
  				isMany: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "CatchEvent",
  		isAbstract: true,
  		superClass: [
  			"Event"
  		],
  		properties: [
  			{
  				name: "parallelMultiple",
  				isAttr: true,
  				type: "Boolean",
  				"default": false
  			},
  			{
  				name: "dataOutputs",
  				type: "DataOutput",
  				isMany: true
  			},
  			{
  				name: "dataOutputAssociations",
  				type: "DataOutputAssociation",
  				isMany: true
  			},
  			{
  				name: "outputSet",
  				type: "OutputSet"
  			},
  			{
  				name: "eventDefinitions",
  				type: "EventDefinition",
  				isMany: true
  			},
  			{
  				name: "eventDefinitionRef",
  				type: "EventDefinition",
  				isMany: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "BoundaryEvent",
  		superClass: [
  			"CatchEvent"
  		],
  		properties: [
  			{
  				name: "cancelActivity",
  				"default": true,
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "attachedToRef",
  				type: "Activity",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "EventDefinition",
  		isAbstract: true,
  		superClass: [
  			"RootElement"
  		]
  	},
  	{
  		name: "CancelEventDefinition",
  		superClass: [
  			"EventDefinition"
  		]
  	},
  	{
  		name: "ErrorEventDefinition",
  		superClass: [
  			"EventDefinition"
  		],
  		properties: [
  			{
  				name: "errorRef",
  				type: "Error",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "TerminateEventDefinition",
  		superClass: [
  			"EventDefinition"
  		]
  	},
  	{
  		name: "EscalationEventDefinition",
  		superClass: [
  			"EventDefinition"
  		],
  		properties: [
  			{
  				name: "escalationRef",
  				type: "Escalation",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "Escalation",
  		properties: [
  			{
  				name: "structureRef",
  				type: "ItemDefinition",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "escalationCode",
  				isAttr: true,
  				type: "String"
  			}
  		],
  		superClass: [
  			"RootElement"
  		]
  	},
  	{
  		name: "CompensateEventDefinition",
  		superClass: [
  			"EventDefinition"
  		],
  		properties: [
  			{
  				name: "waitForCompletion",
  				isAttr: true,
  				type: "Boolean",
  				"default": true
  			},
  			{
  				name: "activityRef",
  				type: "Activity",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "TimerEventDefinition",
  		superClass: [
  			"EventDefinition"
  		],
  		properties: [
  			{
  				name: "timeDate",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			},
  			{
  				name: "timeCycle",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			},
  			{
  				name: "timeDuration",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			}
  		]
  	},
  	{
  		name: "LinkEventDefinition",
  		superClass: [
  			"EventDefinition"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "target",
  				type: "LinkEventDefinition",
  				isReference: true
  			},
  			{
  				name: "source",
  				type: "LinkEventDefinition",
  				isMany: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "MessageEventDefinition",
  		superClass: [
  			"EventDefinition"
  		],
  		properties: [
  			{
  				name: "messageRef",
  				type: "Message",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "operationRef",
  				type: "Operation",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "ConditionalEventDefinition",
  		superClass: [
  			"EventDefinition"
  		],
  		properties: [
  			{
  				name: "condition",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			}
  		]
  	},
  	{
  		name: "SignalEventDefinition",
  		superClass: [
  			"EventDefinition"
  		],
  		properties: [
  			{
  				name: "signalRef",
  				type: "Signal",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "Signal",
  		superClass: [
  			"RootElement"
  		],
  		properties: [
  			{
  				name: "structureRef",
  				type: "ItemDefinition",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "ImplicitThrowEvent",
  		superClass: [
  			"ThrowEvent"
  		]
  	},
  	{
  		name: "DataState",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "ItemAwareElement",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "itemSubjectRef",
  				type: "ItemDefinition",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "dataState",
  				type: "DataState"
  			}
  		]
  	},
  	{
  		name: "DataAssociation",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "sourceRef",
  				type: "ItemAwareElement",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "targetRef",
  				type: "ItemAwareElement",
  				isReference: true
  			},
  			{
  				name: "transformation",
  				type: "FormalExpression",
  				xml: {
  					serialize: "property"
  				}
  			},
  			{
  				name: "assignment",
  				type: "Assignment",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "DataInput",
  		superClass: [
  			"ItemAwareElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "isCollection",
  				"default": false,
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "inputSetRef",
  				type: "InputSet",
  				isMany: true,
  				isVirtual: true,
  				isReference: true
  			},
  			{
  				name: "inputSetWithOptional",
  				type: "InputSet",
  				isMany: true,
  				isVirtual: true,
  				isReference: true
  			},
  			{
  				name: "inputSetWithWhileExecuting",
  				type: "InputSet",
  				isMany: true,
  				isVirtual: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "DataOutput",
  		superClass: [
  			"ItemAwareElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "isCollection",
  				"default": false,
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "outputSetRef",
  				type: "OutputSet",
  				isMany: true,
  				isVirtual: true,
  				isReference: true
  			},
  			{
  				name: "outputSetWithOptional",
  				type: "OutputSet",
  				isMany: true,
  				isVirtual: true,
  				isReference: true
  			},
  			{
  				name: "outputSetWithWhileExecuting",
  				type: "OutputSet",
  				isMany: true,
  				isVirtual: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "InputSet",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "dataInputRefs",
  				type: "DataInput",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "optionalInputRefs",
  				type: "DataInput",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "whileExecutingInputRefs",
  				type: "DataInput",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "outputSetRefs",
  				type: "OutputSet",
  				isMany: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "OutputSet",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "dataOutputRefs",
  				type: "DataOutput",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "inputSetRefs",
  				type: "InputSet",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "optionalOutputRefs",
  				type: "DataOutput",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "whileExecutingOutputRefs",
  				type: "DataOutput",
  				isMany: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "Property",
  		superClass: [
  			"ItemAwareElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "DataInputAssociation",
  		superClass: [
  			"DataAssociation"
  		]
  	},
  	{
  		name: "DataOutputAssociation",
  		superClass: [
  			"DataAssociation"
  		]
  	},
  	{
  		name: "InputOutputSpecification",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "dataInputs",
  				type: "DataInput",
  				isMany: true
  			},
  			{
  				name: "dataOutputs",
  				type: "DataOutput",
  				isMany: true
  			},
  			{
  				name: "inputSets",
  				type: "InputSet",
  				isMany: true
  			},
  			{
  				name: "outputSets",
  				type: "OutputSet",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "DataObject",
  		superClass: [
  			"FlowElement",
  			"ItemAwareElement"
  		],
  		properties: [
  			{
  				name: "isCollection",
  				"default": false,
  				isAttr: true,
  				type: "Boolean"
  			}
  		]
  	},
  	{
  		name: "InputOutputBinding",
  		properties: [
  			{
  				name: "inputDataRef",
  				type: "InputSet",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "outputDataRef",
  				type: "OutputSet",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "operationRef",
  				type: "Operation",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "Assignment",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "from",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			},
  			{
  				name: "to",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			}
  		]
  	},
  	{
  		name: "DataStore",
  		superClass: [
  			"RootElement",
  			"ItemAwareElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "capacity",
  				isAttr: true,
  				type: "Integer"
  			},
  			{
  				name: "isUnlimited",
  				"default": true,
  				isAttr: true,
  				type: "Boolean"
  			}
  		]
  	},
  	{
  		name: "DataStoreReference",
  		superClass: [
  			"ItemAwareElement",
  			"FlowElement"
  		],
  		properties: [
  			{
  				name: "dataStoreRef",
  				type: "DataStore",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "DataObjectReference",
  		superClass: [
  			"ItemAwareElement",
  			"FlowElement"
  		],
  		properties: [
  			{
  				name: "dataObjectRef",
  				type: "DataObject",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "ConversationLink",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "sourceRef",
  				type: "InteractionNode",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "targetRef",
  				type: "InteractionNode",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "ConversationAssociation",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "innerConversationNodeRef",
  				type: "ConversationNode",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "outerConversationNodeRef",
  				type: "ConversationNode",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "CallConversation",
  		superClass: [
  			"ConversationNode"
  		],
  		properties: [
  			{
  				name: "calledCollaborationRef",
  				type: "Collaboration",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "participantAssociations",
  				type: "ParticipantAssociation",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "Conversation",
  		superClass: [
  			"ConversationNode"
  		]
  	},
  	{
  		name: "SubConversation",
  		superClass: [
  			"ConversationNode"
  		],
  		properties: [
  			{
  				name: "conversationNodes",
  				type: "ConversationNode",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "ConversationNode",
  		isAbstract: true,
  		superClass: [
  			"InteractionNode",
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "participantRef",
  				type: "Participant",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "messageFlowRefs",
  				type: "MessageFlow",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "correlationKeys",
  				type: "CorrelationKey",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "GlobalConversation",
  		superClass: [
  			"Collaboration"
  		]
  	},
  	{
  		name: "PartnerEntity",
  		superClass: [
  			"RootElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "participantRef",
  				type: "Participant",
  				isMany: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "PartnerRole",
  		superClass: [
  			"RootElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "participantRef",
  				type: "Participant",
  				isMany: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "CorrelationProperty",
  		superClass: [
  			"RootElement"
  		],
  		properties: [
  			{
  				name: "correlationPropertyRetrievalExpression",
  				type: "CorrelationPropertyRetrievalExpression",
  				isMany: true
  			},
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "type",
  				type: "ItemDefinition",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "Error",
  		superClass: [
  			"RootElement"
  		],
  		properties: [
  			{
  				name: "structureRef",
  				type: "ItemDefinition",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "errorCode",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "CorrelationKey",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "correlationPropertyRef",
  				type: "CorrelationProperty",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "Expression",
  		superClass: [
  			"BaseElement"
  		],
  		isAbstract: false,
  		properties: [
  			{
  				name: "body",
  				isBody: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "FormalExpression",
  		superClass: [
  			"Expression"
  		],
  		properties: [
  			{
  				name: "language",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "evaluatesToTypeRef",
  				type: "ItemDefinition",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "Message",
  		superClass: [
  			"RootElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "itemRef",
  				type: "ItemDefinition",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "ItemDefinition",
  		superClass: [
  			"RootElement"
  		],
  		properties: [
  			{
  				name: "itemKind",
  				type: "ItemKind",
  				isAttr: true
  			},
  			{
  				name: "structureRef",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "isCollection",
  				"default": false,
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "import",
  				type: "Import",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "FlowElement",
  		isAbstract: true,
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "auditing",
  				type: "Auditing"
  			},
  			{
  				name: "monitoring",
  				type: "Monitoring"
  			},
  			{
  				name: "categoryValueRef",
  				type: "CategoryValue",
  				isMany: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "SequenceFlow",
  		superClass: [
  			"FlowElement"
  		],
  		properties: [
  			{
  				name: "isImmediate",
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "conditionExpression",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			},
  			{
  				name: "sourceRef",
  				type: "FlowNode",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "targetRef",
  				type: "FlowNode",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "FlowElementsContainer",
  		isAbstract: true,
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "laneSets",
  				type: "LaneSet",
  				isMany: true
  			},
  			{
  				name: "flowElements",
  				type: "FlowElement",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "CallableElement",
  		isAbstract: true,
  		superClass: [
  			"RootElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "ioSpecification",
  				type: "InputOutputSpecification",
  				xml: {
  					serialize: "property"
  				}
  			},
  			{
  				name: "supportedInterfaceRef",
  				type: "Interface",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "ioBinding",
  				type: "InputOutputBinding",
  				isMany: true,
  				xml: {
  					serialize: "property"
  				}
  			}
  		]
  	},
  	{
  		name: "FlowNode",
  		isAbstract: true,
  		superClass: [
  			"FlowElement"
  		],
  		properties: [
  			{
  				name: "incoming",
  				type: "SequenceFlow",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "outgoing",
  				type: "SequenceFlow",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "lanes",
  				type: "Lane",
  				isMany: true,
  				isVirtual: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "CorrelationPropertyRetrievalExpression",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "messagePath",
  				type: "FormalExpression"
  			},
  			{
  				name: "messageRef",
  				type: "Message",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "CorrelationPropertyBinding",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "dataPath",
  				type: "FormalExpression"
  			},
  			{
  				name: "correlationPropertyRef",
  				type: "CorrelationProperty",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "Resource",
  		superClass: [
  			"RootElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "resourceParameters",
  				type: "ResourceParameter",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "ResourceParameter",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "isRequired",
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "type",
  				type: "ItemDefinition",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "CorrelationSubscription",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "correlationKeyRef",
  				type: "CorrelationKey",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "correlationPropertyBinding",
  				type: "CorrelationPropertyBinding",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "MessageFlow",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "sourceRef",
  				type: "InteractionNode",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "targetRef",
  				type: "InteractionNode",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "messageRef",
  				type: "Message",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "MessageFlowAssociation",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "innerMessageFlowRef",
  				type: "MessageFlow",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "outerMessageFlowRef",
  				type: "MessageFlow",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "InteractionNode",
  		isAbstract: true,
  		properties: [
  			{
  				name: "incomingConversationLinks",
  				type: "ConversationLink",
  				isMany: true,
  				isVirtual: true,
  				isReference: true
  			},
  			{
  				name: "outgoingConversationLinks",
  				type: "ConversationLink",
  				isMany: true,
  				isVirtual: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "Participant",
  		superClass: [
  			"InteractionNode",
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "interfaceRef",
  				type: "Interface",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "participantMultiplicity",
  				type: "ParticipantMultiplicity"
  			},
  			{
  				name: "endPointRefs",
  				type: "EndPoint",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "processRef",
  				type: "Process",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "ParticipantAssociation",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "innerParticipantRef",
  				type: "Participant",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "outerParticipantRef",
  				type: "Participant",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "ParticipantMultiplicity",
  		properties: [
  			{
  				name: "minimum",
  				"default": 0,
  				isAttr: true,
  				type: "Integer"
  			},
  			{
  				name: "maximum",
  				"default": 1,
  				isAttr: true,
  				type: "Integer"
  			}
  		],
  		superClass: [
  			"BaseElement"
  		]
  	},
  	{
  		name: "Collaboration",
  		superClass: [
  			"RootElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "isClosed",
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "participants",
  				type: "Participant",
  				isMany: true
  			},
  			{
  				name: "messageFlows",
  				type: "MessageFlow",
  				isMany: true
  			},
  			{
  				name: "artifacts",
  				type: "Artifact",
  				isMany: true
  			},
  			{
  				name: "conversations",
  				type: "ConversationNode",
  				isMany: true
  			},
  			{
  				name: "conversationAssociations",
  				type: "ConversationAssociation"
  			},
  			{
  				name: "participantAssociations",
  				type: "ParticipantAssociation",
  				isMany: true
  			},
  			{
  				name: "messageFlowAssociations",
  				type: "MessageFlowAssociation",
  				isMany: true
  			},
  			{
  				name: "correlationKeys",
  				type: "CorrelationKey",
  				isMany: true
  			},
  			{
  				name: "choreographyRef",
  				type: "Choreography",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "conversationLinks",
  				type: "ConversationLink",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "ChoreographyActivity",
  		isAbstract: true,
  		superClass: [
  			"FlowNode"
  		],
  		properties: [
  			{
  				name: "participantRef",
  				type: "Participant",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "initiatingParticipantRef",
  				type: "Participant",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "correlationKeys",
  				type: "CorrelationKey",
  				isMany: true
  			},
  			{
  				name: "loopType",
  				type: "ChoreographyLoopType",
  				"default": "None",
  				isAttr: true
  			}
  		]
  	},
  	{
  		name: "CallChoreography",
  		superClass: [
  			"ChoreographyActivity"
  		],
  		properties: [
  			{
  				name: "calledChoreographyRef",
  				type: "Choreography",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "participantAssociations",
  				type: "ParticipantAssociation",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "SubChoreography",
  		superClass: [
  			"ChoreographyActivity",
  			"FlowElementsContainer"
  		],
  		properties: [
  			{
  				name: "artifacts",
  				type: "Artifact",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "ChoreographyTask",
  		superClass: [
  			"ChoreographyActivity"
  		],
  		properties: [
  			{
  				name: "messageFlowRef",
  				type: "MessageFlow",
  				isMany: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "Choreography",
  		superClass: [
  			"Collaboration",
  			"FlowElementsContainer"
  		]
  	},
  	{
  		name: "GlobalChoreographyTask",
  		superClass: [
  			"Choreography"
  		],
  		properties: [
  			{
  				name: "initiatingParticipantRef",
  				type: "Participant",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "TextAnnotation",
  		superClass: [
  			"Artifact"
  		],
  		properties: [
  			{
  				name: "text",
  				type: "String"
  			},
  			{
  				name: "textFormat",
  				"default": "text/plain",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "Group",
  		superClass: [
  			"Artifact"
  		],
  		properties: [
  			{
  				name: "categoryValueRef",
  				type: "CategoryValue",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "Association",
  		superClass: [
  			"Artifact"
  		],
  		properties: [
  			{
  				name: "associationDirection",
  				type: "AssociationDirection",
  				isAttr: true
  			},
  			{
  				name: "sourceRef",
  				type: "BaseElement",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "targetRef",
  				type: "BaseElement",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "Category",
  		superClass: [
  			"RootElement"
  		],
  		properties: [
  			{
  				name: "categoryValue",
  				type: "CategoryValue",
  				isMany: true
  			},
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "Artifact",
  		isAbstract: true,
  		superClass: [
  			"BaseElement"
  		]
  	},
  	{
  		name: "CategoryValue",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "categorizedFlowElements",
  				type: "FlowElement",
  				isMany: true,
  				isVirtual: true,
  				isReference: true
  			},
  			{
  				name: "value",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "Activity",
  		isAbstract: true,
  		superClass: [
  			"FlowNode"
  		],
  		properties: [
  			{
  				name: "isForCompensation",
  				"default": false,
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "default",
  				type: "SequenceFlow",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "ioSpecification",
  				type: "InputOutputSpecification",
  				xml: {
  					serialize: "property"
  				}
  			},
  			{
  				name: "boundaryEventRefs",
  				type: "BoundaryEvent",
  				isMany: true,
  				isReference: true
  			},
  			{
  				name: "properties",
  				type: "Property",
  				isMany: true
  			},
  			{
  				name: "dataInputAssociations",
  				type: "DataInputAssociation",
  				isMany: true
  			},
  			{
  				name: "dataOutputAssociations",
  				type: "DataOutputAssociation",
  				isMany: true
  			},
  			{
  				name: "startQuantity",
  				"default": 1,
  				isAttr: true,
  				type: "Integer"
  			},
  			{
  				name: "resources",
  				type: "ResourceRole",
  				isMany: true
  			},
  			{
  				name: "completionQuantity",
  				"default": 1,
  				isAttr: true,
  				type: "Integer"
  			},
  			{
  				name: "loopCharacteristics",
  				type: "LoopCharacteristics"
  			}
  		]
  	},
  	{
  		name: "ServiceTask",
  		superClass: [
  			"Task"
  		],
  		properties: [
  			{
  				name: "implementation",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "operationRef",
  				type: "Operation",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "SubProcess",
  		superClass: [
  			"Activity",
  			"FlowElementsContainer",
  			"InteractionNode"
  		],
  		properties: [
  			{
  				name: "triggeredByEvent",
  				"default": false,
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "artifacts",
  				type: "Artifact",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "LoopCharacteristics",
  		isAbstract: true,
  		superClass: [
  			"BaseElement"
  		]
  	},
  	{
  		name: "MultiInstanceLoopCharacteristics",
  		superClass: [
  			"LoopCharacteristics"
  		],
  		properties: [
  			{
  				name: "isSequential",
  				"default": false,
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "behavior",
  				type: "MultiInstanceBehavior",
  				"default": "All",
  				isAttr: true
  			},
  			{
  				name: "loopCardinality",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			},
  			{
  				name: "loopDataInputRef",
  				type: "ItemAwareElement",
  				isReference: true
  			},
  			{
  				name: "loopDataOutputRef",
  				type: "ItemAwareElement",
  				isReference: true
  			},
  			{
  				name: "inputDataItem",
  				type: "DataInput",
  				xml: {
  					serialize: "property"
  				}
  			},
  			{
  				name: "outputDataItem",
  				type: "DataOutput",
  				xml: {
  					serialize: "property"
  				}
  			},
  			{
  				name: "complexBehaviorDefinition",
  				type: "ComplexBehaviorDefinition",
  				isMany: true
  			},
  			{
  				name: "completionCondition",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			},
  			{
  				name: "oneBehaviorEventRef",
  				type: "EventDefinition",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "noneBehaviorEventRef",
  				type: "EventDefinition",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "StandardLoopCharacteristics",
  		superClass: [
  			"LoopCharacteristics"
  		],
  		properties: [
  			{
  				name: "testBefore",
  				"default": false,
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "loopCondition",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			},
  			{
  				name: "loopMaximum",
  				type: "Integer",
  				isAttr: true
  			}
  		]
  	},
  	{
  		name: "CallActivity",
  		superClass: [
  			"Activity",
  			"InteractionNode"
  		],
  		properties: [
  			{
  				name: "calledElement",
  				type: "String",
  				isAttr: true
  			}
  		]
  	},
  	{
  		name: "Task",
  		superClass: [
  			"Activity",
  			"InteractionNode"
  		]
  	},
  	{
  		name: "SendTask",
  		superClass: [
  			"Task"
  		],
  		properties: [
  			{
  				name: "implementation",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "operationRef",
  				type: "Operation",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "messageRef",
  				type: "Message",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "ReceiveTask",
  		superClass: [
  			"Task"
  		],
  		properties: [
  			{
  				name: "implementation",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "instantiate",
  				"default": false,
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "operationRef",
  				type: "Operation",
  				isAttr: true,
  				isReference: true
  			},
  			{
  				name: "messageRef",
  				type: "Message",
  				isAttr: true,
  				isReference: true
  			}
  		]
  	},
  	{
  		name: "ScriptTask",
  		superClass: [
  			"Task"
  		],
  		properties: [
  			{
  				name: "scriptFormat",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "script",
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "BusinessRuleTask",
  		superClass: [
  			"Task"
  		],
  		properties: [
  			{
  				name: "implementation",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "AdHocSubProcess",
  		superClass: [
  			"SubProcess"
  		],
  		properties: [
  			{
  				name: "completionCondition",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			},
  			{
  				name: "ordering",
  				type: "AdHocOrdering",
  				isAttr: true
  			},
  			{
  				name: "cancelRemainingInstances",
  				"default": true,
  				isAttr: true,
  				type: "Boolean"
  			}
  		]
  	},
  	{
  		name: "Transaction",
  		superClass: [
  			"SubProcess"
  		],
  		properties: [
  			{
  				name: "protocol",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "method",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "GlobalScriptTask",
  		superClass: [
  			"GlobalTask"
  		],
  		properties: [
  			{
  				name: "scriptLanguage",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "script",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "GlobalBusinessRuleTask",
  		superClass: [
  			"GlobalTask"
  		],
  		properties: [
  			{
  				name: "implementation",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "ComplexBehaviorDefinition",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "condition",
  				type: "FormalExpression"
  			},
  			{
  				name: "event",
  				type: "ImplicitThrowEvent"
  			}
  		]
  	},
  	{
  		name: "ResourceRole",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "resourceRef",
  				type: "Resource",
  				isReference: true
  			},
  			{
  				name: "resourceParameterBindings",
  				type: "ResourceParameterBinding",
  				isMany: true
  			},
  			{
  				name: "resourceAssignmentExpression",
  				type: "ResourceAssignmentExpression"
  			},
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "ResourceParameterBinding",
  		properties: [
  			{
  				name: "expression",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			},
  			{
  				name: "parameterRef",
  				type: "ResourceParameter",
  				isAttr: true,
  				isReference: true
  			}
  		],
  		superClass: [
  			"BaseElement"
  		]
  	},
  	{
  		name: "ResourceAssignmentExpression",
  		properties: [
  			{
  				name: "expression",
  				type: "Expression",
  				xml: {
  					serialize: "xsi:type"
  				}
  			}
  		],
  		superClass: [
  			"BaseElement"
  		]
  	},
  	{
  		name: "Import",
  		properties: [
  			{
  				name: "importType",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "location",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "namespace",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "Definitions",
  		superClass: [
  			"BaseElement"
  		],
  		properties: [
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "targetNamespace",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "expressionLanguage",
  				"default": "http://www.w3.org/1999/XPath",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "typeLanguage",
  				"default": "http://www.w3.org/2001/XMLSchema",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "imports",
  				type: "Import",
  				isMany: true
  			},
  			{
  				name: "extensions",
  				type: "Extension",
  				isMany: true
  			},
  			{
  				name: "rootElements",
  				type: "RootElement",
  				isMany: true
  			},
  			{
  				name: "diagrams",
  				isMany: true,
  				type: "bpmndi:BPMNDiagram"
  			},
  			{
  				name: "exporter",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "relationships",
  				type: "Relationship",
  				isMany: true
  			},
  			{
  				name: "exporterVersion",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	}
  ];
  var enumerations$3 = [
  	{
  		name: "ProcessType",
  		literalValues: [
  			{
  				name: "None"
  			},
  			{
  				name: "Public"
  			},
  			{
  				name: "Private"
  			}
  		]
  	},
  	{
  		name: "GatewayDirection",
  		literalValues: [
  			{
  				name: "Unspecified"
  			},
  			{
  				name: "Converging"
  			},
  			{
  				name: "Diverging"
  			},
  			{
  				name: "Mixed"
  			}
  		]
  	},
  	{
  		name: "EventBasedGatewayType",
  		literalValues: [
  			{
  				name: "Parallel"
  			},
  			{
  				name: "Exclusive"
  			}
  		]
  	},
  	{
  		name: "RelationshipDirection",
  		literalValues: [
  			{
  				name: "None"
  			},
  			{
  				name: "Forward"
  			},
  			{
  				name: "Backward"
  			},
  			{
  				name: "Both"
  			}
  		]
  	},
  	{
  		name: "ItemKind",
  		literalValues: [
  			{
  				name: "Physical"
  			},
  			{
  				name: "Information"
  			}
  		]
  	},
  	{
  		name: "ChoreographyLoopType",
  		literalValues: [
  			{
  				name: "None"
  			},
  			{
  				name: "Standard"
  			},
  			{
  				name: "MultiInstanceSequential"
  			},
  			{
  				name: "MultiInstanceParallel"
  			}
  		]
  	},
  	{
  		name: "AssociationDirection",
  		literalValues: [
  			{
  				name: "None"
  			},
  			{
  				name: "One"
  			},
  			{
  				name: "Both"
  			}
  		]
  	},
  	{
  		name: "MultiInstanceBehavior",
  		literalValues: [
  			{
  				name: "None"
  			},
  			{
  				name: "One"
  			},
  			{
  				name: "All"
  			},
  			{
  				name: "Complex"
  			}
  		]
  	},
  	{
  		name: "AdHocOrdering",
  		literalValues: [
  			{
  				name: "Parallel"
  			},
  			{
  				name: "Sequential"
  			}
  		]
  	}
  ];
  var xml$1 = {
  	tagAlias: "lowerCase",
  	typePrefix: "t"
  };
  var BpmnPackage = {
  	name: name$5,
  	uri: uri$5,
  	prefix: prefix$5,
  	associations: associations$5,
  	types: types$5,
  	enumerations: enumerations$3,
  	xml: xml$1
  };

  var name$4 = "BPMNDI";
  var uri$4 = "http://www.omg.org/spec/BPMN/20100524/DI";
  var prefix$4 = "bpmndi";
  var types$4 = [
  	{
  		name: "BPMNDiagram",
  		properties: [
  			{
  				name: "plane",
  				type: "BPMNPlane",
  				redefines: "di:Diagram#rootElement"
  			},
  			{
  				name: "labelStyle",
  				type: "BPMNLabelStyle",
  				isMany: true
  			}
  		],
  		superClass: [
  			"di:Diagram"
  		]
  	},
  	{
  		name: "BPMNPlane",
  		properties: [
  			{
  				name: "bpmnElement",
  				isAttr: true,
  				isReference: true,
  				type: "bpmn:BaseElement",
  				redefines: "di:DiagramElement#modelElement"
  			}
  		],
  		superClass: [
  			"di:Plane"
  		]
  	},
  	{
  		name: "BPMNShape",
  		properties: [
  			{
  				name: "bpmnElement",
  				isAttr: true,
  				isReference: true,
  				type: "bpmn:BaseElement",
  				redefines: "di:DiagramElement#modelElement"
  			},
  			{
  				name: "isHorizontal",
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "isExpanded",
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "isMarkerVisible",
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "label",
  				type: "BPMNLabel"
  			},
  			{
  				name: "isMessageVisible",
  				isAttr: true,
  				type: "Boolean"
  			},
  			{
  				name: "participantBandKind",
  				type: "ParticipantBandKind",
  				isAttr: true
  			},
  			{
  				name: "choreographyActivityShape",
  				type: "BPMNShape",
  				isAttr: true,
  				isReference: true
  			}
  		],
  		superClass: [
  			"di:LabeledShape"
  		]
  	},
  	{
  		name: "BPMNEdge",
  		properties: [
  			{
  				name: "label",
  				type: "BPMNLabel"
  			},
  			{
  				name: "bpmnElement",
  				isAttr: true,
  				isReference: true,
  				type: "bpmn:BaseElement",
  				redefines: "di:DiagramElement#modelElement"
  			},
  			{
  				name: "sourceElement",
  				isAttr: true,
  				isReference: true,
  				type: "di:DiagramElement",
  				redefines: "di:Edge#source"
  			},
  			{
  				name: "targetElement",
  				isAttr: true,
  				isReference: true,
  				type: "di:DiagramElement",
  				redefines: "di:Edge#target"
  			},
  			{
  				name: "messageVisibleKind",
  				type: "MessageVisibleKind",
  				isAttr: true,
  				"default": "initiating"
  			}
  		],
  		superClass: [
  			"di:LabeledEdge"
  		]
  	},
  	{
  		name: "BPMNLabel",
  		properties: [
  			{
  				name: "labelStyle",
  				type: "BPMNLabelStyle",
  				isAttr: true,
  				isReference: true,
  				redefines: "di:DiagramElement#style"
  			}
  		],
  		superClass: [
  			"di:Label"
  		]
  	},
  	{
  		name: "BPMNLabelStyle",
  		properties: [
  			{
  				name: "font",
  				type: "dc:Font"
  			}
  		],
  		superClass: [
  			"di:Style"
  		]
  	}
  ];
  var enumerations$2 = [
  	{
  		name: "ParticipantBandKind",
  		literalValues: [
  			{
  				name: "top_initiating"
  			},
  			{
  				name: "middle_initiating"
  			},
  			{
  				name: "bottom_initiating"
  			},
  			{
  				name: "top_non_initiating"
  			},
  			{
  				name: "middle_non_initiating"
  			},
  			{
  				name: "bottom_non_initiating"
  			}
  		]
  	},
  	{
  		name: "MessageVisibleKind",
  		literalValues: [
  			{
  				name: "initiating"
  			},
  			{
  				name: "non_initiating"
  			}
  		]
  	}
  ];
  var associations$4 = [
  ];
  var BpmnDiPackage = {
  	name: name$4,
  	uri: uri$4,
  	prefix: prefix$4,
  	types: types$4,
  	enumerations: enumerations$2,
  	associations: associations$4
  };

  var name$3 = "DC";
  var uri$3 = "http://www.omg.org/spec/DD/20100524/DC";
  var prefix$3 = "dc";
  var types$3 = [
  	{
  		name: "Boolean"
  	},
  	{
  		name: "Integer"
  	},
  	{
  		name: "Real"
  	},
  	{
  		name: "String"
  	},
  	{
  		name: "Font",
  		properties: [
  			{
  				name: "name",
  				type: "String",
  				isAttr: true
  			},
  			{
  				name: "size",
  				type: "Real",
  				isAttr: true
  			},
  			{
  				name: "isBold",
  				type: "Boolean",
  				isAttr: true
  			},
  			{
  				name: "isItalic",
  				type: "Boolean",
  				isAttr: true
  			},
  			{
  				name: "isUnderline",
  				type: "Boolean",
  				isAttr: true
  			},
  			{
  				name: "isStrikeThrough",
  				type: "Boolean",
  				isAttr: true
  			}
  		]
  	},
  	{
  		name: "Point",
  		properties: [
  			{
  				name: "x",
  				type: "Real",
  				"default": "0",
  				isAttr: true
  			},
  			{
  				name: "y",
  				type: "Real",
  				"default": "0",
  				isAttr: true
  			}
  		]
  	},
  	{
  		name: "Bounds",
  		properties: [
  			{
  				name: "x",
  				type: "Real",
  				"default": "0",
  				isAttr: true
  			},
  			{
  				name: "y",
  				type: "Real",
  				"default": "0",
  				isAttr: true
  			},
  			{
  				name: "width",
  				type: "Real",
  				isAttr: true
  			},
  			{
  				name: "height",
  				type: "Real",
  				isAttr: true
  			}
  		]
  	}
  ];
  var associations$3 = [
  ];
  var DcPackage = {
  	name: name$3,
  	uri: uri$3,
  	prefix: prefix$3,
  	types: types$3,
  	associations: associations$3
  };

  var name$2 = "DI";
  var uri$2 = "http://www.omg.org/spec/DD/20100524/DI";
  var prefix$2 = "di";
  var types$2 = [
  	{
  		name: "DiagramElement",
  		isAbstract: true,
  		properties: [
  			{
  				name: "id",
  				isAttr: true,
  				isId: true,
  				type: "String"
  			},
  			{
  				name: "extension",
  				type: "Extension"
  			},
  			{
  				name: "owningDiagram",
  				type: "Diagram",
  				isReadOnly: true,
  				isVirtual: true,
  				isReference: true
  			},
  			{
  				name: "owningElement",
  				type: "DiagramElement",
  				isReadOnly: true,
  				isVirtual: true,
  				isReference: true
  			},
  			{
  				name: "modelElement",
  				isReadOnly: true,
  				isVirtual: true,
  				isReference: true,
  				type: "Element"
  			},
  			{
  				name: "style",
  				type: "Style",
  				isReadOnly: true,
  				isVirtual: true,
  				isReference: true
  			},
  			{
  				name: "ownedElement",
  				type: "DiagramElement",
  				isReadOnly: true,
  				isMany: true,
  				isVirtual: true
  			}
  		]
  	},
  	{
  		name: "Node",
  		isAbstract: true,
  		superClass: [
  			"DiagramElement"
  		]
  	},
  	{
  		name: "Edge",
  		isAbstract: true,
  		superClass: [
  			"DiagramElement"
  		],
  		properties: [
  			{
  				name: "source",
  				type: "DiagramElement",
  				isReadOnly: true,
  				isVirtual: true,
  				isReference: true
  			},
  			{
  				name: "target",
  				type: "DiagramElement",
  				isReadOnly: true,
  				isVirtual: true,
  				isReference: true
  			},
  			{
  				name: "waypoint",
  				isUnique: false,
  				isMany: true,
  				type: "dc:Point",
  				xml: {
  					serialize: "xsi:type"
  				}
  			}
  		]
  	},
  	{
  		name: "Diagram",
  		isAbstract: true,
  		properties: [
  			{
  				name: "id",
  				isAttr: true,
  				isId: true,
  				type: "String"
  			},
  			{
  				name: "rootElement",
  				type: "DiagramElement",
  				isReadOnly: true,
  				isVirtual: true
  			},
  			{
  				name: "name",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "documentation",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "resolution",
  				isAttr: true,
  				type: "Real"
  			},
  			{
  				name: "ownedStyle",
  				type: "Style",
  				isReadOnly: true,
  				isMany: true,
  				isVirtual: true
  			}
  		]
  	},
  	{
  		name: "Shape",
  		isAbstract: true,
  		superClass: [
  			"Node"
  		],
  		properties: [
  			{
  				name: "bounds",
  				type: "dc:Bounds"
  			}
  		]
  	},
  	{
  		name: "Plane",
  		isAbstract: true,
  		superClass: [
  			"Node"
  		],
  		properties: [
  			{
  				name: "planeElement",
  				type: "DiagramElement",
  				subsettedProperty: "DiagramElement-ownedElement",
  				isMany: true
  			}
  		]
  	},
  	{
  		name: "LabeledEdge",
  		isAbstract: true,
  		superClass: [
  			"Edge"
  		],
  		properties: [
  			{
  				name: "ownedLabel",
  				type: "Label",
  				isReadOnly: true,
  				subsettedProperty: "DiagramElement-ownedElement",
  				isMany: true,
  				isVirtual: true
  			}
  		]
  	},
  	{
  		name: "LabeledShape",
  		isAbstract: true,
  		superClass: [
  			"Shape"
  		],
  		properties: [
  			{
  				name: "ownedLabel",
  				type: "Label",
  				isReadOnly: true,
  				subsettedProperty: "DiagramElement-ownedElement",
  				isMany: true,
  				isVirtual: true
  			}
  		]
  	},
  	{
  		name: "Label",
  		isAbstract: true,
  		superClass: [
  			"Node"
  		],
  		properties: [
  			{
  				name: "bounds",
  				type: "dc:Bounds"
  			}
  		]
  	},
  	{
  		name: "Style",
  		isAbstract: true,
  		properties: [
  			{
  				name: "id",
  				isAttr: true,
  				isId: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "Extension",
  		properties: [
  			{
  				name: "values",
  				isMany: true,
  				type: "Element"
  			}
  		]
  	}
  ];
  var associations$2 = [
  ];
  var xml = {
  	tagAlias: "lowerCase"
  };
  var DiPackage = {
  	name: name$2,
  	uri: uri$2,
  	prefix: prefix$2,
  	types: types$2,
  	associations: associations$2,
  	xml: xml
  };

  var name$1 = "bpmn.io colors for BPMN";
  var uri$1 = "http://bpmn.io/schema/bpmn/biocolor/1.0";
  var prefix$1 = "bioc";
  var types$1 = [
  	{
  		name: "ColoredShape",
  		"extends": [
  			"bpmndi:BPMNShape"
  		],
  		properties: [
  			{
  				name: "stroke",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "fill",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "ColoredEdge",
  		"extends": [
  			"bpmndi:BPMNEdge"
  		],
  		properties: [
  			{
  				name: "stroke",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "fill",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	}
  ];
  var enumerations$1 = [
  ];
  var associations$1 = [
  ];
  var BiocPackage = {
  	name: name$1,
  	uri: uri$1,
  	prefix: prefix$1,
  	types: types$1,
  	enumerations: enumerations$1,
  	associations: associations$1
  };

  var name = "BPMN in Color";
  var uri = "http://www.omg.org/spec/BPMN/non-normative/color/1.0";
  var prefix = "color";
  var types = [
  	{
  		name: "ColoredLabel",
  		"extends": [
  			"bpmndi:BPMNLabel"
  		],
  		properties: [
  			{
  				name: "color",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "ColoredShape",
  		"extends": [
  			"bpmndi:BPMNShape"
  		],
  		properties: [
  			{
  				name: "background-color",
  				isAttr: true,
  				type: "String"
  			},
  			{
  				name: "border-color",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	},
  	{
  		name: "ColoredEdge",
  		"extends": [
  			"bpmndi:BPMNEdge"
  		],
  		properties: [
  			{
  				name: "border-color",
  				isAttr: true,
  				type: "String"
  			}
  		]
  	}
  ];
  var enumerations = [
  ];
  var associations = [
  ];
  var BpmnInColorPackage = {
  	name: name,
  	uri: uri,
  	prefix: prefix,
  	types: types,
  	enumerations: enumerations,
  	associations: associations
  };

  const packages = {
    bpmn: BpmnPackage,
    bpmndi: BpmnDiPackage,
    dc: DcPackage,
    di: DiPackage,
    bioc: BiocPackage,
    color: BpmnInColorPackage
  };

  function SimpleBpmnModdle(additionalPackages, options) {
    const pks = assign({}, packages, additionalPackages);

    return new BpmnModdle(pks, options);
  }

  function isConnection(element) {
    return !!element.sourceRef;
  }

  function isBoundaryEvent(element) {
    return !!element.attachedToRef;
  }

  function findElementInTree(currentElement, targetElement, visited = new Set()) {

    if (currentElement === targetElement) return true;

    if (visited.has(currentElement)) return false;

    visited.add(currentElement);

    // If currentElement has no outgoing connections, return false
    if (!currentElement.outgoing || currentElement.outgoing.length === 0) return false;

    // Recursively check each outgoing element
    for (let nextElement of currentElement.outgoing.map(out => out.targetRef)) {
      if (findElementInTree(nextElement, targetElement, visited)) {
        return true;
      }
    }

    return false;
  }

  class Grid {
    constructor() {
      this.grid = [];
    }

    add(element, position) {
      if (!position) {
        this._addStart(element);
        return;
      }

      const [ row, col ] = position;
      if (!row && !col) {
        this._addStart(element);
      }

      if (!this.grid[row]) {
        this.grid[row] = [];
      }

      if (this.grid[row][col]) {
        throw new Error('Grid is occupied please ensure the place you insert at is not occupied');
      }

      this.grid[row][col] = element;
    }

    createRow(afterIndex) {
      if (!afterIndex) {
        this.grid.push([]);
      }

      this.grid.splice(afterIndex + 1, 0, []);
    }

    _addStart(element) {
      this.grid.push([ element ]);
    }

    addAfter(element, newElement) {
      if (!element) {
        this._addStart(newElement);
      }
      const [ row, col ] = this.find(element);
      this.grid[row].splice(col + 1, 0, newElement);
    }

    addBelow(element, newElement) {
      if (!element) {
        this._addStart(newElement);
      }

      const [ row, col ] = this.find(element);

      // We are at the bottom of the current grid - add empty row below
      if (!this.grid[row + 1]) {
        this.grid[row + 1] = [];
      }

      // The element below is already occupied - insert new row
      if (this.grid[row + 1][col]) {
        this.grid.splice(row + 1, 0, []);
      }

      if (this.grid[row + 1][col]) {
        throw new Error('Grid is occupied and we could not find a place - this should not happen');
      }

      this.grid[row + 1][col] = newElement;
    }

    find(element) {
      let row, col;
      row = this.grid.findIndex((row) => {
        col = row.findIndex((el) => {
          return el === element;
        });

        return col !== -1;
      });

      return [ row, col ];
    }

    get(row, col) {
      return (this.grid[row] || [])[col];
    }

    getElementsInRange({ row: startRow, col: startCol }, { row: endRow, col: endCol }) {
      const elements = [];

      if (startRow > endRow) {
        [ startRow, endRow ] = [ endRow, startRow ];
      }

      if (startCol > endCol) {
        [ startCol, endCol ] = [ endCol, startCol ];
      }

      for (let row = startRow; row <= endRow; row++) {
        for (let col = startCol; col <= endCol; col++) {
          const element = this.get(row, col);

          if (element) {
            elements.push(element);
          }
        }
      }

      return elements;
    }

    adjustGridPosition(element) {
      let [ row, col ] = this.find(element);
      const [ , maxCol ] = this.getGridDimensions();

      if (col < maxCol - 1) {

        // add element in next column
        this.grid[row].length = maxCol;
        this.grid[row][maxCol] = element;
        this.grid[row][col] = null;

      }
    }

    adjustRowForMultipleIncoming(elements, currentElement) {
      const results = elements.map(element => this.find(element));

      // filter only rows that currently exist, excluding any future or non-existent rows
      const lowestRow = Math.min(...results
        .map(result => result[0])
        .filter(row => row >= 0));

      const [ row , col ] = this.find(currentElement);

      // if element doesn't already exist in current row, add element
      if (lowestRow < row && !this.grid[lowestRow][col]) {
        this.grid[lowestRow][col] = currentElement;
        this.grid[row][col] = null;
      }
    }

    adjustColumnForMultipleIncoming(elements, currentElement) {
      const results = elements.map(element => this.find(element));

      // filter only col that currently exist, excluding any future or non-existent col
      const maxCol = Math.max(...results
        .map(result => result[1])
        .filter(col => col >= 0));

      const [ row , col ] = this.find(currentElement);

      // add to the next column
      if (maxCol + 1 > col) {
        this.grid[row][maxCol + 1] = currentElement;
        this.grid[row][col] = null;
      }
    }

    getAllElements() {
      const elements = [];

      for (let row = 0; row < this.grid.length; row++) {
        for (let col = 0; col < this.grid[row].length; col++) {
          const element = this.get(row, col);

          if (element) {
            elements.push(element);
          }
        }
      }

      return elements;
    }

    getGridDimensions() {
      const numRows = this.grid.length;
      let maxCols = 0;

      for (let i = 0; i < numRows; i++) {
        const currentRowLength = this.grid[i].length;
        if (currentRowLength > maxCols) {
          maxCols = currentRowLength;
        }
      }

      return [ numRows , maxCols ];
    }

    elementsByPosition() {
      const elements = [];

      this.grid.forEach((row, rowIndex) => {
        row.forEach((element, colIndex) => {
          if (!element) {
            return;
          }
          elements.push({
            element,
            row: rowIndex,
            col: colIndex
          });
        });
      });

      return elements;
    }

    getElementsTotal() {
      const flattenedGrid = this.grid.flat();
      const uniqueElements = new Set(flattenedGrid.filter(value => value));
      return uniqueElements.size;
    }
  }

  class DiFactory {
    constructor(moddle) {
      this.moddle = moddle;
    }

    create(type, attrs) {
      return this.moddle.create(type, attrs || {});
    }

    createDiBounds(bounds) {
      return this.create('dc:Bounds', bounds);
    }

    createDiLabel() {
      return this.create('bpmndi:BPMNLabel', {
        bounds: this.createDiBounds()
      });
    }

    createDiShape(semantic, bounds, attrs) {
      return this.create('bpmndi:BPMNShape', assign({
        bpmnElement: semantic,
        bounds: this.createDiBounds(bounds)
      }, attrs));
    }

    createDiWaypoints(waypoints) {
      var self = this;

      return map(waypoints, function(pos) {
        return self.createDiWaypoint(pos);
      });
    }

    createDiWaypoint(point) {
      return this.create('dc:Point', pick(point, [ 'x', 'y' ]));
    }

    createDiEdge(semantic, waypoints, attrs) {
      return this.create('bpmndi:BPMNEdge', assign({
        bpmnElement: semantic,
        waypoint: this.createDiWaypoints(waypoints)
      }, attrs));
    }

    createDiPlane(attrs) {
      return this.create('bpmndi:BPMNPlane', attrs);
    }

    createDiDiagram(attrs) {
      return this.create('bpmndi:BPMNDiagram', attrs);
    }
  }

  function getDefaultSize(element) {
    if (is(element, 'bpmn:SubProcess')) {
      return { width: 100, height: 80 };
    }

    if (is(element, 'bpmn:Task')) {
      return { width: 100, height: 80 };
    }

    if (is(element, 'bpmn:Gateway')) {
      return { width: 50, height: 50 };
    }

    if (is(element, 'bpmn:Event')) {
      return { width: 36, height: 36 };
    }

    if (is(element, 'bpmn:Participant')) {
      return { width: 400, height: 100 };
    }

    if (is(element, 'bpmn:Lane')) {
      return { width: 400, height: 100 };
    }

    if (is(element, 'bpmn:DataObjectReference')) {
      return { width: 36, height: 50 };
    }

    if (is(element, 'bpmn:DataStoreReference')) {
      return { width: 50, height: 50 };
    }

    if (is(element, 'bpmn:TextAnnotation')) {
      return { width: 100, height: 30 };
    }

    return { width: 100, height: 80 };
  }

  function is(element, type) {
    return element.$instanceOf(type);
  }

  const DEFAULT_CELL_WIDTH = 150;
  const DEFAULT_CELL_HEIGHT = 140;

  function getMid(bounds) {
    return {
      x: bounds.x + bounds.width / 2,
      y: bounds.y + bounds.height / 2
    };
  }

  function getDockingPoint(point, rectangle, dockingDirection = 'r', targetOrientation = 'top-left') {

    // ensure we end up with a specific docking direction
    // based on the targetOrientation, if <h|v> is being passed

    if (dockingDirection === 'h') {
      dockingDirection = /left/.test(targetOrientation) ? 'l' : 'r';
    }

    if (dockingDirection === 'v') {
      dockingDirection = /top/.test(targetOrientation) ? 't' : 'b';
    }

    if (dockingDirection === 't') {
      return { original: point, x: point.x, y: rectangle.y };
    }

    if (dockingDirection === 'r') {
      return { original: point, x: rectangle.x + rectangle.width, y: point.y };
    }

    if (dockingDirection === 'b') {
      return { original: point, x: point.x, y: rectangle.y + rectangle.height };
    }

    if (dockingDirection === 'l') {
      return { original: point, x: rectangle.x, y: point.y };
    }

    throw new Error('unexpected dockingDirection: <' + dockingDirection + '>');
  }

  /**
       * Modified Manhattan layout: Uses space between grid coloumns to route connections
       * if direct connection is not possible.
       * @param {*} source
       * @param {*} target
       * @returns waypoints
       */
  function connectElements(source, target, layoutGrid) {
    const sourceDi = source.di;
    const targetDi = target.di;

    const sourceBounds = sourceDi.get('bounds');
    const targetBounds = targetDi.get('bounds');

    const sourceMid = getMid(sourceBounds);
    const targetMid = getMid(targetBounds);

    const dX = target.gridPosition.col - source.gridPosition.col;
    const dY = target.gridPosition.row - source.gridPosition.row;

    const dockingSource = `${(dY > 0 ? 'bottom' : 'top')}-${dX > 0 ? 'right' : 'left'}`;
    const dockingTarget = `${(dY > 0 ? 'top' : 'bottom')}-${dX > 0 ? 'left' : 'right'}`;

    // Source === Target ==> Build loop
    if (dX === 0 && dY === 0) {
      const { x, y } = coordinatesToPosition(source.gridPosition.row, source.gridPosition.col);
      return [
        getDockingPoint(sourceMid, sourceBounds, 'r', dockingSource),
        { x: x + DEFAULT_CELL_WIDTH, y: sourceMid.y },
        { x: x + DEFAULT_CELL_WIDTH, y: y },
        { x: targetMid.x, y: y },
        getDockingPoint(targetMid, targetBounds, 't', dockingTarget)
      ];
    }

    // connect horizontally
    if (dY === 0) {
      if (isDirectPathBlocked(source, target, layoutGrid)) {

        // Route on bottom
        return [
          getDockingPoint(sourceMid, sourceBounds, 'b'),
          { x: sourceMid.x, y: sourceMid.y + DEFAULT_CELL_HEIGHT / 2 },
          { x: targetMid.x, y: sourceMid.y + DEFAULT_CELL_HEIGHT / 2 },
          getDockingPoint(targetMid, targetBounds, 'b')
        ];
      } else {

        // if space is clear, connect directly
        return [
          getDockingPoint(sourceMid, sourceBounds, 'h', dockingSource),
          getDockingPoint(targetMid, targetBounds, 'h', dockingTarget)
        ];
      }
    }

    // connect vertically
    if (dX === 0) {
      if (isDirectPathBlocked(source, target, layoutGrid)) {

        // Route parallel
        const yOffset = -Math.sign(dY) * DEFAULT_CELL_HEIGHT / 2;
        return [
          getDockingPoint(sourceMid, sourceBounds, 'r'),
          { x: sourceMid.x + DEFAULT_CELL_WIDTH / 2, y: sourceMid.y }, // out right
          { x: targetMid.x + DEFAULT_CELL_WIDTH / 2, y: targetMid.y + yOffset },
          { x: targetMid.x, y: targetMid.y + yOffset },
          getDockingPoint(targetMid, targetBounds, Math.sign(yOffset) > 0 ? 'b' : 't')
        ];
      } else {

        // if space is clear, connect directly
        return [ getDockingPoint(sourceMid, sourceBounds, 'v', dockingSource),
          getDockingPoint(targetMid, targetBounds, 'v', dockingTarget)
        ];
      }
    }

    // negative dX indicates connection from future to past
    if (dX < 0 && dY <= 0) {
      return [
        getDockingPoint(sourceMid, sourceBounds, 'b'),
        { x: sourceMid.x, y: sourceMid.y + DEFAULT_CELL_HEIGHT / 2 },
        { x: targetMid.x, y: sourceMid.y + DEFAULT_CELL_HEIGHT / 2 },
        getDockingPoint(targetMid, targetBounds, 'b')
      ];
    }
    const directManhattan = directManhattanConnect(source, target, layoutGrid);

    if (directManhattan) {
      const startPoint = getDockingPoint(sourceMid, sourceBounds, directManhattan[0], dockingSource);
      const endPoint = getDockingPoint(targetMid, targetBounds, directManhattan[1], dockingTarget);

      const midPoint = directManhattan[0] === 'h' ? { x: endPoint.x, y: startPoint.y } : { x: startPoint.x, y: endPoint.y };

      return [
        startPoint,
        midPoint,
        endPoint
      ];
    }
    const yOffset = -Math.sign(dY) * DEFAULT_CELL_HEIGHT / 2;

    return [
      getDockingPoint(sourceMid, sourceBounds, 'r', dockingSource),
      { x: sourceMid.x + DEFAULT_CELL_WIDTH / 2, y: sourceMid.y }, // out right
      { x: sourceMid.x + DEFAULT_CELL_WIDTH / 2, y: targetMid.y + yOffset }, // to target row
      { x: targetMid.x - DEFAULT_CELL_WIDTH / 2, y: targetMid.y + yOffset }, // to target column
      { x: targetMid.x - DEFAULT_CELL_WIDTH / 2, y: targetMid.y }, // to mid
      getDockingPoint(targetMid, targetBounds, 'l', dockingTarget)
    ];
  }

  // helpers /////
  function coordinatesToPosition(row, col) {
    return {
      width: DEFAULT_CELL_WIDTH,
      height: DEFAULT_CELL_HEIGHT,
      x: col * DEFAULT_CELL_WIDTH,
      y: row * DEFAULT_CELL_HEIGHT
    };
  }

  function getBounds(element, row, col, attachedTo) {
    const { width, height } = getDefaultSize(element);

    // Center in cell
    if (!attachedTo) {
      return {
        width, height,
        x: (col * DEFAULT_CELL_WIDTH) + (DEFAULT_CELL_WIDTH - width) / 2,
        y: row * DEFAULT_CELL_HEIGHT + (DEFAULT_CELL_HEIGHT - height) / 2
      };
    }

    const hostBounds = getBounds(attachedTo, row, col);

    return {
      width, height,
      x: Math.round(hostBounds.x + hostBounds.width / 2 - width / 2),
      y: Math.round(hostBounds.y + hostBounds.height - height / 2)
    };
  }

  function isDirectPathBlocked(source, target, layoutGrid) {
    const { row: sourceRow, col: sourceCol } = source.gridPosition;
    const { row: targetRow, col: targetCol } = target.gridPosition;

    const dX = targetCol - sourceCol;
    const dY = targetRow - sourceRow;

    let totalElements = 0;

    if (dX) {
      totalElements += layoutGrid.getElementsInRange({ row: sourceRow, col: sourceCol }, { row: sourceRow, col: targetCol }).length;
    }

    if (dY) {
      totalElements += layoutGrid.getElementsInRange({ row: sourceRow, col: targetCol }, { row: targetRow, col: targetCol }).length;
    }

    return totalElements > 2;
  }

  function directManhattanConnect(source, target, layoutGrid) {
    const { row: sourceRow, col: sourceCol } = source.gridPosition;
    const { row: targetRow, col: targetCol } = target.gridPosition;

    const dX = targetCol - sourceCol;
    const dY = targetRow - sourceRow;

    // Only directly connect left-to-right flow
    if (!(dX > 0 && dY !== 0)) {
      return;
    }

    // If below, go down then horizontal
    if (dY > 0) {
      let totalElements = 0;
      const bendPoint = { row: targetRow, col: sourceCol };
      totalElements += layoutGrid.getElementsInRange({ row: sourceRow, col: sourceCol }, bendPoint).length;
      totalElements += layoutGrid.getElementsInRange(bendPoint, { row: targetRow, col: targetCol }).length;

      return totalElements > 2 ? false : [ 'v', 'h' ];
    } else {

      // If above, go horizontal than vertical
      let totalElements = 0;
      const bendPoint = { row: sourceRow, col: targetCol };

      totalElements += layoutGrid.getElementsInRange({ row: sourceRow, col: sourceCol }, bendPoint).length;
      totalElements += layoutGrid.getElementsInRange(bendPoint, { row: targetRow, col: targetCol }).length;

      return totalElements > 2 ? false : [ 'h', 'v' ];
    }
  }

  var attacherHandler = {
    'addToGrid': ({ element, grid, visited }) => {
      const nextElements = [];

      const attachedOutgoing = (element.attachers || [])
        .map(attacher => (attacher.outgoing || []).reverse())
        .flat()
        .map(out => out.targetRef);

      // handle boundary events
      attachedOutgoing.forEach((nextElement, index, arr) => {
        if (visited.has(nextElement)) {
          return;
        }

        // Add below and to the right of the element
        insertIntoGrid(nextElement, element, grid);
        nextElements.push(nextElement);
      });

      return nextElements;
    },

    'createElementDi': ({ element, row, col, diFactory }) => {
      const hostBounds = getBounds(element, row, col);

      const DIs = [];
      (element.attachers || []).forEach((att, i, arr) => {
        att.gridPosition = { row, col };
        const bounds = getBounds(att, row, col, element);

        // distribute along lower edge
        bounds.x = hostBounds.x + (i + 1) * (hostBounds.width / (arr.length + 1)) - bounds.width / 2;

        const attacherDi = diFactory.createDiShape(att, bounds, {
          id: att.id + '_di'
        });
        att.di = attacherDi;
        att.gridPosition = { row, col };

        DIs.push(attacherDi);
      });

      return DIs;
    },

    'createConnectionDi': ({ element, row, col, layoutGrid, diFactory }) => {
      const attachers = element.attachers || [];

      return attachers.flatMap(att => {
        const outgoing = att.outgoing || [];

        return outgoing.map(out => {
          const target = out.targetRef;
          const waypoints = connectElements(att, target, layoutGrid);

          // Correct waypoints if they don't automatically attach to the bottom
          ensureExitBottom(att, waypoints, [ row, col ]);

          const connectionDi = diFactory.createDiEdge(out, waypoints, {
            id: out.id + '_di'
          });

          return connectionDi;
        });
      });
    }
  };


  function insertIntoGrid(newElement, host, grid) {
    const [ row, col ] = grid.find(host);

    // Grid is occupied
    if (grid.get(row + 1, col) || grid.get(row + 1, col + 1)) {
      grid.createRow(row);
    }

    grid.add(newElement, [ row + 1, col + 1 ]);
  }

  function ensureExitBottom(source, waypoints, [ row, col ]) {

    const sourceDi = source.di;
    const sourceBounds = sourceDi.get('bounds');
    const sourceMid = getMid(sourceBounds);

    const dockingPoint = getDockingPoint(sourceMid, sourceBounds, 'b');
    if (waypoints[0].x === dockingPoint.x && waypoints[0].y === dockingPoint.y) {
      return;
    }

    if (waypoints.length === 2) {
      const newStart = [
        dockingPoint,
        { x: dockingPoint.x, y: (row + 1) * DEFAULT_CELL_HEIGHT },
        { x: (col + 1) * DEFAULT_CELL_WIDTH, y: (row + 1) * DEFAULT_CELL_HEIGHT },
        { x: (col + 1) * DEFAULT_CELL_WIDTH, y: (row + 0.5) * DEFAULT_CELL_HEIGHT },
      ];

      waypoints.splice(0, 1, ...newStart);
      return;
    }

    // add waypoints to exit bottom and connect to existing path
    const newStart = [
      dockingPoint,
      { x: dockingPoint.x, y: (row + 1) * DEFAULT_CELL_HEIGHT },
      { x: waypoints[1].x, y: (row + 1) * DEFAULT_CELL_HEIGHT },
    ];

    waypoints.splice(0, 1, ...newStart);
    return;
  }

  var elementHandler = {
    'createElementDi': ({ element, row, col, diFactory }) => {

      const bounds = getBounds(element, row, col);

      const options = {
        id: element.id + '_di'
      };

      if (is(element, 'bpmn:ExclusiveGateway')) {
        options.isMarkerVisible = true;
      }

      const shapeDi = diFactory.createDiShape(element, bounds, options);
      element.di = shapeDi;
      element.gridPosition = { row, col };

      return shapeDi;
    }
  };

  var outgoingHandler = {
    'addToGrid': ({ element, grid, visited, stack }) => {
      let nextElements = [];

      // Handle outgoing paths
      const outgoing = (element.outgoing || [])
        .map(out => out.targetRef)
        .filter(el => el);

      let previousElement = null;

      if (outgoing.length > 1 && isNextElementTasks(outgoing)) {
        grid.adjustGridPosition(element);
      }

      outgoing.forEach((nextElement, index, arr) => {
        if (visited.has(nextElement)) {
          return;
        }

        // Prevents revisiting future incoming elements and ensures proper traversal without early exit.
        if ((previousElement || stack.length > 0) && isFutureIncoming(nextElement, visited) && !checkForLoop(nextElement, visited)) {
          return;
        }

        if (!previousElement) {
          grid.addAfter(element, nextElement);
        }

        else if (is(element, 'bpmn:ExclusiveGateway') && is(nextElement, 'bpmn:ExclusiveGateway')) {
          grid.addAfter(previousElement, nextElement);
        }
        else {
          grid.addBelow(arr[index - 1], nextElement);
        }

        // Is self-looping
        if (nextElement !== element) {
          previousElement = nextElement;
        }

        nextElements.unshift(nextElement);
        visited.add(nextElement);
      });

      // Sort elements by priority to ensure proper stack placement
      nextElements = sortByType(nextElements, 'bpmn:ExclusiveGateway'); // TODO: sort by priority
      return nextElements;
    },

    'createConnectionDi': ({ element, row, col, layoutGrid, diFactory }) => {
      const outgoing = element.outgoing || [];

      return outgoing.map(out => {
        const target = out.targetRef;
        const waypoints = connectElements(element, target, layoutGrid);

        const connectionDi = diFactory.createDiEdge(out, waypoints, {
          id: out.id + '_di'
        });

        return connectionDi;
      });

    }
  };


  // helpers /////

  function sortByType(arr, type) {
    const nonMatching = arr.filter(item => !is(item,type));
    const matching = arr.filter(item => is(item,type));

    return [ ...matching, ...nonMatching ];

  }

  function checkForLoop(element, visited) {
    for (const incomingElement of element.incoming) {
      if (!visited.has(incomingElement.sourceRef)) {
        return findElementInTree(element, incomingElement.sourceRef);
      }
    }
  }


  function isFutureIncoming(element, visited) {
    if (element.incoming.length > 1) {
      for (const incomingElement of element.incoming) {
        if (!visited.has(incomingElement.sourceRef)) {
          return true;
        }
      }
    }
    return false;
  }

  function isNextElementTasks(elements) {
    return elements.every(element => is(element, 'bpmn:Task'));
  }

  var incomingHandler = {
    'addToGrid': ({ element, grid, visited }) => {
      const nextElements = [];

      const incoming = (element.incoming || [])
        .map(out => out.sourceRef)
        .filter(el => el);

      // adjust the row if it is empty
      if (incoming.length > 1) {
        grid.adjustColumnForMultipleIncoming(incoming, element);
        grid.adjustRowForMultipleIncoming(incoming, element);
      }
      return nextElements;
    },
  };

  const handlers = [ elementHandler, incomingHandler, outgoingHandler, attacherHandler ];

  class Layouter {
    constructor() {
      this.moddle = new SimpleBpmnModdle();
      this.diFactory = new DiFactory(this.moddle);
      this._handlers = handlers;
    }

    handle(operation, options) {
      return this._handlers
        .filter(handler => isFunction(handler[operation]))
        .map(handler => handler[operation](options));

    }

    async layoutProcess(xml) {
      const { rootElement } = await this.moddle.fromXML(xml);

      this.diagram = rootElement;

      const root = this.getProcess();

      if (root) {
        this.cleanDi();
        this.handlePlane(root);
      }

      return (await this.moddle.toXML(this.diagram, { format: true })).xml;
    }

    handlePlane(planeElement) {
      const layout = this.createGridLayout(planeElement);
      this.generateDi(planeElement, layout);
    }

    cleanDi() {
      this.diagram.diagrams = [];
    }

    createGridLayout(root) {
      const grid = new Grid();

      const flowElements = root.flowElements || [];
      const elements = flowElements.filter(el => !is(el,'bpmn:SequenceFlow'));

      // check for empty process/subprocess
      if (!flowElements) {
        return grid;
      }

      const startingElements = flowElements.filter(el => {
        return !isConnection(el) && !isBoundaryEvent(el) && (!el.incoming || el.length === 0);
      });

      const boundaryEvents = flowElements.filter(el => isBoundaryEvent(el));
      boundaryEvents.forEach(boundaryEvent => {
        const attachedTask = boundaryEvent.attachedToRef;
        const attachers = attachedTask.attachers || [];
        attachers.push(boundaryEvent);
        attachedTask.attachers = attachers;
      });

      // Depth-first-search
      const stack = [ ...startingElements ];
      const visited = new Set();

      startingElements.forEach(el => {
        grid.add(el);
        visited.add(el);
      });

      this.handleGrid(grid,visited,stack);

      if (grid.getElementsTotal() != elements.length) {
        const gridElements = grid.getAllElements();
        const missingElements = elements.filter(el => !gridElements.includes(el) && !isBoundaryEvent(el));
        if (missingElements.length > 1) {
          stack.push(missingElements[0]);
          grid.add(missingElements[0]);
          visited.add(missingElements[0]);
          this.handleGrid(grid,visited,stack);
        }
      }

      return grid;
    }

    generateDi(root, layoutGrid) {
      const diFactory = this.diFactory;

      // Step 0: Create Root element
      const diagram = this.diagram;

      var planeDi = diFactory.createDiPlane({
        id: 'BPMNPlane_' + root.id,
        bpmnElement: root
      });
      var diagramDi = diFactory.createDiDiagram({
        id: 'BPMNDiagram_' + root.id,
        plane: planeDi
      });

      // deepest subprocess is added first - insert at the front
      diagram.diagrams.unshift(diagramDi);

      const planeElement = planeDi.get('planeElement');

      // Step 1: Create DI for all elements
      layoutGrid.elementsByPosition().forEach(({ element, row, col }) => {
        const dis = this
          .handle('createElementDi', { element, row, col, layoutGrid, diFactory })
          .flat();

        planeElement.push(...dis);
      });

      // Step 2: Create DI for all connections
      layoutGrid.elementsByPosition().forEach(({ element, row, col }) => {
        const dis = this
          .handle('createConnectionDi', { element, row, col, layoutGrid, diFactory })
          .flat();

        planeElement.push(...dis);
      });
    }

    handleGrid(grid, visited, stack) {
      while (stack.length > 0) {
        const currentElement = stack.pop();

        if (is(currentElement, 'bpmn:SubProcess')) {
          this.handlePlane(currentElement);
        }

        const nextElements = this.handle('addToGrid', { element: currentElement, grid, visited, stack });

        nextElements.flat().forEach(el => {
          stack.push(el);
          visited.add(el);
        });
      }
    }

    getProcess() {
      return this.diagram.get('rootElements').find(el => el.$type === 'bpmn:Process');
    }
  }

  function layoutProcess(xml) {
    return new Layouter().layoutProcess(xml);
  }

  exports.layoutProcess = layoutProcess;

}));
//# sourceMappingURL=bpmn-auto-layout.js.map
